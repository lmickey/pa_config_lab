"""
Terraform Generator - Generates Terraform files from CloudConfig.

Renders Jinja2 templates and generates terraform.tfvars.json from
the CloudConfig model to create a complete Terraform deployment.
"""

import json
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from config.models.cloud import CloudConfig

logger = logging.getLogger(__name__)


class TerraformGenerator:
    """
    Generates Terraform deployment files from CloudConfig.

    Takes a CloudConfig object and produces:
    - terraform.tfvars.json with all variable values
    - Rendered .tf files from Jinja2 templates
    - provider.tf with Azure provider configuration
    """

    # Default template directory (relative to this file)
    DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates" / "azure"

    def __init__(
        self,
        cloud_config: CloudConfig,
        output_dir: str,
        template_dir: Optional[str] = None,
    ):
        """
        Initialize Terraform generator.

        Args:
            cloud_config: CloudConfig with deployment settings
            output_dir: Directory to write Terraform files
            template_dir: Optional custom template directory
        """
        if not JINJA2_AVAILABLE:
            raise ImportError("Jinja2 is required for Terraform generation. Install with: pip install Jinja2")

        self.cloud_config = cloud_config
        self.output_dir = Path(output_dir)
        self.template_dir = Path(template_dir) if template_dir else self.DEFAULT_TEMPLATE_DIR

        # Validate cloud config
        if not cloud_config.deployment:
            raise ValueError("CloudConfig must have deployment settings")

        # Set up Jinja2 environment
        self._setup_jinja_env()

    def _setup_jinja_env(self):
        """Configure Jinja2 environment with custom filters."""
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.jinja_env.filters['to_json'] = lambda x: json.dumps(x, indent=2)
        self.jinja_env.filters['to_hcl_list'] = self._to_hcl_list
        self.jinja_env.filters['to_hcl_map'] = self._to_hcl_map
        self.jinja_env.filters['sanitize_name'] = self._sanitize_terraform_name

    @staticmethod
    def _to_hcl_list(items: List[str]) -> str:
        """Convert Python list to HCL list format."""
        if not items:
            return "[]"
        quoted = [f'"{item}"' for item in items]
        return f"[{', '.join(quoted)}]"

    @staticmethod
    def _to_hcl_map(mapping: Dict[str, Any]) -> str:
        """Convert Python dict to HCL map format."""
        if not mapping:
            return "{}"
        pairs = []
        for k, v in mapping.items():
            if isinstance(v, str):
                pairs.append(f'"{k}" = "{v}"')
            elif isinstance(v, bool):
                pairs.append(f'"{k}" = {str(v).lower()}')
            elif isinstance(v, (int, float)):
                pairs.append(f'"{k}" = {v}')
            else:
                pairs.append(f'"{k}" = "{v}"')
        return "{\n    " + "\n    ".join(pairs) + "\n  }"

    @staticmethod
    def _sanitize_terraform_name(name: str) -> str:
        """Sanitize name for Terraform resource naming."""
        import re
        # Replace non-alphanumeric with underscore
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        # Ensure starts with letter
        if name and not name[0].isalpha():
            name = 'r_' + name
        return name.lower()

    def generate(self, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate all Terraform files.

        Args:
            credentials: Optional credentials dict to include in tfvars

        Returns:
            Dict with generation results:
            - output_dir: Path to generated files
            - files_created: List of created files
            - tfvars_path: Path to terraform.tfvars.json
        """
        logger.info(f"Generating Terraform files in {self.output_dir}")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        files_created = []

        # Generate terraform.tfvars.json
        tfvars_path = self._generate_tfvars(credentials)
        files_created.append(str(tfvars_path))

        # Generate provider.tf
        provider_path = self._generate_provider()
        files_created.append(str(provider_path))

        # Generate main.tf (networking)
        main_path = self._generate_main()
        files_created.append(str(main_path))

        # Generate firewall resources
        if self.cloud_config.firewalls:
            fw_path = self._generate_firewalls()
            files_created.append(str(fw_path))

        # Generate ION device resources
        if self.cloud_config.ion_devices:
            ion_path = self._generate_ion_devices()
            files_created.append(str(ion_path))

        # Generate Panorama if present
        if self.cloud_config.panorama:
            pan_path = self._generate_panorama()
            files_created.append(str(pan_path))

        # Generate supporting VMs
        if self.cloud_config.all_supporting_vms:
            support_path = self._generate_supporting_vms()
            files_created.append(str(support_path))

        # Generate bootstrap packages and storage
        if self.cloud_config.firewalls or self.cloud_config.panorama:
            bootstrap_files = self._generate_bootstrap(credentials)
            files_created.extend(bootstrap_files)

            # Generate bootstrap storage template
            storage_path = self._generate_bootstrap_storage()
            files_created.append(str(storage_path))

        # Generate outputs.tf
        outputs_path = self._generate_outputs()
        files_created.append(str(outputs_path))

        # Generate variables.tf
        vars_path = self._generate_variables()
        files_created.append(str(vars_path))

        logger.info(f"Generated {len(files_created)} Terraform files")

        return {
            'output_dir': str(self.output_dir),
            'files_created': files_created,
            'tfvars_path': str(tfvars_path),
            'resource_group': self.cloud_config.deployment.resource_group,
        }

    def _generate_tfvars(self, credentials: Optional[Dict[str, Any]] = None) -> Path:
        """Generate terraform.tfvars.json from CloudConfig."""
        tfvars = self.cloud_config.to_terraform_vars()

        # Add credentials if provided
        if credentials:
            tfvars['credentials'] = credentials

        # Add metadata
        tfvars['_metadata'] = {
            'generated_at': datetime.utcnow().isoformat(),
            'generator': 'pa_config_lab.terraform.TerraformGenerator',
        }

        tfvars_path = self.output_dir / "terraform.tfvars.json"
        with open(tfvars_path, 'w') as f:
            json.dump(tfvars, f, indent=2)

        logger.debug(f"Generated {tfvars_path}")
        return tfvars_path

    def _generate_provider(self) -> Path:
        """Generate provider.tf with Azure provider configuration."""
        template = self._get_template('provider.tf.j2')

        content = template.render(
            deployment=self.cloud_config.deployment,
            subscription_id=self.cloud_config.deployment.subscription_id,
            tenant_id=self.cloud_config.deployment.tenant_id,
        )

        provider_path = self.output_dir / "provider.tf"
        with open(provider_path, 'w') as f:
            f.write(content)

        logger.debug(f"Generated {provider_path}")
        return provider_path

    def _generate_main(self) -> Path:
        """Generate main.tf with networking resources."""
        template = self._get_template('main.tf.j2')

        deployment = self.cloud_config.deployment
        content = template.render(
            deployment=deployment,
            resource_group=deployment.resource_group,
            location=deployment.location,
            vnet_name=deployment.vnet_name,
            address_space=deployment.virtual_network.address_space,
            subnets=deployment.virtual_network.subnets,
            tags=deployment.tags,
        )

        main_path = self.output_dir / "main.tf"
        with open(main_path, 'w') as f:
            f.write(content)

        logger.debug(f"Generated {main_path}")
        return main_path

    def _generate_firewalls(self) -> Path:
        """Generate firewall.tf with VM-Series firewall resources."""
        template = self._get_template('firewall.tf.j2')

        content = template.render(
            firewalls=self.cloud_config.firewalls,
            deployment=self.cloud_config.deployment,
            resource_group=self.cloud_config.deployment.resource_group,
        )

        fw_path = self.output_dir / "firewall.tf"
        with open(fw_path, 'w') as f:
            f.write(content)

        logger.debug(f"Generated {fw_path}")
        return fw_path

    def _generate_ion_devices(self) -> Path:
        """Generate ion.tf with SD-WAN ION device resources."""
        template = self._get_template('ion.tf.j2')

        content = template.render(
            ion_devices=self.cloud_config.ion_devices,
            deployment=self.cloud_config.deployment,
            resource_group=self.cloud_config.deployment.resource_group,
        )

        ion_path = self.output_dir / "ion.tf"
        with open(ion_path, 'w') as f:
            f.write(content)

        logger.debug(f"Generated {ion_path}")
        return ion_path

    def _generate_panorama(self) -> Path:
        """Generate panorama.tf with Panorama VM resources."""
        template = self._get_template('panorama.tf.j2')

        content = template.render(
            panorama=self.cloud_config.panorama,
            deployment=self.cloud_config.deployment,
            resource_group=self.cloud_config.deployment.resource_group,
        )

        pan_path = self.output_dir / "panorama.tf"
        with open(pan_path, 'w') as f:
            f.write(content)

        logger.debug(f"Generated {pan_path}")
        return pan_path

    def _generate_supporting_vms(self) -> Path:
        """Generate supporting_vms.tf with server/client/ZTNA resources."""
        template = self._get_template('supporting_vms.tf.j2')

        content = template.render(
            servers=self.cloud_config.servers,
            clients=self.cloud_config.clients,
            ztna_connectors=self.cloud_config.ztna_connectors,
            deployment=self.cloud_config.deployment,
            resource_group=self.cloud_config.deployment.resource_group,
        )

        support_path = self.output_dir / "supporting_vms.tf"
        with open(support_path, 'w') as f:
            f.write(content)

        logger.debug(f"Generated {support_path}")
        return support_path

    def _generate_bootstrap(self, credentials: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate bootstrap packages for firewalls.

        Creates bootstrap directory structure with init-cfg.txt and bootstrap.xml
        for each firewall.

        Args:
            credentials: Optional credentials dict

        Returns:
            List of created file paths
        """
        from terraform.bootstrap import BootstrapConfig, BootstrapGenerator

        files_created = []
        bootstrap_dir = self.output_dir / "bootstrap"

        # Generate bootstrap for each firewall
        for fw in self.cloud_config.firewalls:
            fw_bootstrap_dir = bootstrap_dir / fw.name

            # Get firewall credentials
            fw_creds = None
            if credentials and 'firewall' in credentials:
                fw_creds = credentials['firewall']

            # Create bootstrap config
            config = BootstrapConfig.from_cloud_firewall(
                fw,
                self.cloud_config.deployment,
                fw_creds
            )

            # Generate bootstrap files
            generator = BootstrapGenerator(config)
            created = generator.generate(str(fw_bootstrap_dir))
            files_created.extend(created.values())

            logger.info(f"Generated bootstrap package for {fw.name}")

        # Generate bootstrap for Panorama if present
        if self.cloud_config.panorama:
            pan_bootstrap_dir = bootstrap_dir / self.cloud_config.panorama.name

            pan_creds = None
            if credentials and 'panorama' in credentials:
                pan_creds = credentials['panorama']

            # Panorama uses simpler bootstrap (just init-cfg.txt)
            config = BootstrapConfig(
                hostname=self.cloud_config.panorama.hostname,
                admin_username=pan_creds.get('username', 'admin') if pan_creds else 'admin',
                admin_password=pan_creds.get('password') if pan_creds else None,
            )

            generator = BootstrapGenerator(config)
            # Only generate init-cfg.txt for Panorama
            init_cfg_content = generator.generate_init_cfg()

            pan_config_dir = pan_bootstrap_dir / "config"
            pan_config_dir.mkdir(parents=True, exist_ok=True)

            init_cfg_path = pan_config_dir / "init-cfg.txt"
            with open(init_cfg_path, 'w') as f:
                f.write(init_cfg_content)
            files_created.append(str(init_cfg_path))

            logger.info(f"Generated bootstrap package for {self.cloud_config.panorama.name}")

        return files_created

    def _generate_bootstrap_storage(self) -> Path:
        """Generate bootstrap_storage.tf with storage account and blob containers."""
        template = self._get_template('bootstrap_storage.tf.j2')

        content = template.render(
            firewalls=self.cloud_config.firewalls,
            panorama=self.cloud_config.panorama,
            deployment=self.cloud_config.deployment,
        )

        storage_path = self.output_dir / "bootstrap_storage.tf"
        with open(storage_path, 'w') as f:
            f.write(content)

        logger.debug(f"Generated {storage_path}")
        return storage_path

    def _generate_outputs(self) -> Path:
        """Generate outputs.tf with deployment outputs."""
        template = self._get_template('outputs.tf.j2')

        content = template.render(
            firewalls=self.cloud_config.firewalls,
            ion_devices=self.cloud_config.ion_devices,
            panorama=self.cloud_config.panorama,
            servers=self.cloud_config.servers,
            clients=self.cloud_config.clients,
            ztna_connectors=self.cloud_config.ztna_connectors,
        )

        outputs_path = self.output_dir / "outputs.tf"
        with open(outputs_path, 'w') as f:
            f.write(content)

        logger.debug(f"Generated {outputs_path}")
        return outputs_path

    def _generate_variables(self) -> Path:
        """Generate variables.tf with variable declarations."""
        template = self._get_template('variables.tf.j2')

        content = template.render(
            deployment=self.cloud_config.deployment,
            has_firewalls=bool(self.cloud_config.firewalls),
            has_ion_devices=bool(self.cloud_config.ion_devices),
            has_panorama=self.cloud_config.panorama is not None,
            has_supporting_vms=bool(self.cloud_config.all_supporting_vms),
        )

        vars_path = self.output_dir / "variables.tf"
        with open(vars_path, 'w') as f:
            f.write(content)

        logger.debug(f"Generated {vars_path}")
        return vars_path

    def _get_template(self, template_name: str):
        """
        Get a Jinja2 template, falling back to default if not found.

        Args:
            template_name: Template filename (e.g., 'main.tf.j2')

        Returns:
            Jinja2 template object
        """
        try:
            return self.jinja_env.get_template(template_name)
        except Exception as e:
            logger.warning(f"Template {template_name} not found, using default")
            # Return a simple default template
            return self.jinja_env.from_string(
                f"# Auto-generated {template_name}\n# Template not found - using placeholder\n"
            )

    def clean(self):
        """Remove generated Terraform files."""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
            logger.info(f"Cleaned {self.output_dir}")
