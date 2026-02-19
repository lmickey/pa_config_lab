"""
Services generator for POV Builder.

Generates DNS (bind9), web application (nginx), and PKI certificate
infrastructure for ServerVM cloud-init deployment.
"""

from typing import Dict, Any, List, Optional
import logging
import textwrap

logger = logging.getLogger(__name__)


# ============================================================================
# DEFAULT APPLICATION DEFINITIONS
# ============================================================================

DEFAULT_APPLICATIONS = [
    {'subdomain': 'hr', 'name': 'HR Portal', 'category': 'HR',
     'description': 'Human Resources self-service portal for employees',
     'color': '#2196F3', 'icon': 'people'},
    {'subdomain': 'erp', 'name': 'ERP System', 'category': 'Business',
     'description': 'Enterprise Resource Planning and operations management',
     'color': '#4CAF50', 'icon': 'business'},
    {'subdomain': 'finance', 'name': 'Finance Dashboard', 'category': 'Finance',
     'description': 'Financial reporting and analytics dashboard',
     'color': '#FF9800', 'icon': 'trending_up'},
    {'subdomain': 'it', 'name': 'IT Management', 'category': 'IT',
     'description': 'IT infrastructure and asset management console',
     'color': '#9C27B0', 'icon': 'computer'},
    {'subdomain': 'helpdesk', 'name': 'Helpdesk', 'category': 'IT',
     'description': 'Internal helpdesk and support ticket system',
     'color': '#00BCD4', 'icon': 'support'},
    {'subdomain': 'tickets', 'name': 'Ticket System', 'category': 'IT',
     'description': 'Issue tracking and project ticket management',
     'color': '#607D8B', 'icon': 'confirmation_number'},
    {'subdomain': 'wiki', 'name': 'Knowledge Base', 'category': 'Knowledge',
     'description': 'Internal wiki and knowledge management platform',
     'color': '#795548', 'icon': 'menu_book'},
    {'subdomain': 'crm', 'name': 'CRM', 'category': 'Sales',
     'description': 'Customer relationship management and sales pipeline',
     'color': '#E91E63', 'icon': 'contacts'},
    {'subdomain': 'mail', 'name': 'Webmail', 'category': 'Communication',
     'description': 'Corporate webmail and calendar application',
     'color': '#3F51B5', 'icon': 'mail'},
    {'subdomain': 'files', 'name': 'File Sharing', 'category': 'Collaboration',
     'description': 'Secure file sharing and document collaboration',
     'color': '#009688', 'icon': 'folder_shared'},
    {'subdomain': 'projects', 'name': 'Project Management', 'category': 'Collaboration',
     'description': 'Project planning, tracking, and team collaboration',
     'color': '#FF5722', 'icon': 'assignment'},
    {'subdomain': 'code', 'name': 'Code Repository', 'category': 'Development',
     'description': 'Source code repository and version control system',
     'color': '#424242', 'icon': 'code'},
    {'subdomain': 'monitor', 'name': 'Monitoring Dashboard', 'category': 'Operations',
     'description': 'Infrastructure monitoring and alerting dashboard',
     'color': '#F44336', 'icon': 'monitor_heart'},
    {'subdomain': 'vpn', 'name': 'VPN Portal', 'category': 'Security',
     'description': 'VPN client download and connection management portal',
     'color': '#1B5E20', 'icon': 'vpn_lock'},
    {'subdomain': 'inventory', 'name': 'Inventory Management', 'category': 'Operations',
     'description': 'Asset inventory and supply chain management',
     'color': '#BF360C', 'icon': 'inventory_2'},
]

# ============================================================================
# DEFAULT EMPLOYEE DEFINITIONS
# ============================================================================

DEFAULT_EMPLOYEES = [
    {'name': 'Alice Johnson', 'email_prefix': 'ajohnson', 'department': 'Engineering', 'title': 'Senior Developer'},
    {'name': 'Bob Martinez', 'email_prefix': 'bmartinez', 'department': 'Sales', 'title': 'Account Executive'},
    {'name': 'Carol Chen', 'email_prefix': 'cchen', 'department': 'Finance', 'title': 'Financial Analyst'},
    {'name': 'David Thompson', 'email_prefix': 'dthompson', 'department': 'IT', 'title': 'Systems Administrator'},
    {'name': 'Emily Park', 'email_prefix': 'epark', 'department': 'HR', 'title': 'HR Manager'},
    {'name': 'Frank Williams', 'email_prefix': 'fwilliams', 'department': 'Operations', 'title': 'Operations Lead'},
    {'name': 'Grace Lee', 'email_prefix': 'glee', 'department': 'Marketing', 'title': 'Marketing Director'},
    {'name': 'Henry Davis', 'email_prefix': 'hdavis', 'department': 'Security', 'title': 'Security Analyst'},
]


# ============================================================================
# DNS CONFIGURATION GENERATOR
# ============================================================================

class DNSConfigGenerator:
    """Generates bind9 DNS zone files and configuration."""

    def __init__(self, domain: str, server_ip: str, applications: List[Dict] = None):
        self.domain = domain
        self.server_ip = server_ip
        self.applications = applications or DEFAULT_APPLICATIONS

    def generate_zone_file(self) -> str:
        """Generate bind9 zone file with SOA and A records."""
        records = []
        for app in self.applications:
            subdomain = app['subdomain']
            records.append(f"{subdomain:20s} IN  A       {self.server_ip}")

        records_block = "\n".join(records)

        return textwrap.dedent(f"""\
            ; Zone file for {self.domain}
            ; Generated by PA Config Lab POV Builder
            $TTL    86400
            @       IN      SOA     ns1.{self.domain}. admin.{self.domain}. (
                                2024010101  ; Serial
                                3600        ; Refresh
                                1800        ; Retry
                                604800      ; Expire
                                86400 )     ; Minimum TTL

            ; Name servers
            @                    IN  NS      ns1.{self.domain}.
            ns1                  IN  A       {self.server_ip}

            ; Root domain
            @                    IN  A       {self.server_ip}

            ; Application records
            {records_block}
        """)

    def generate_named_conf_local(self) -> str:
        """Generate bind9 named.conf.local for the zone."""
        return textwrap.dedent(f"""\
            // DNS zone for {self.domain}
            // Generated by PA Config Lab POV Builder

            zone "{self.domain}" {{
                type master;
                file "/etc/bind/zones/db.{self.domain}";
                allow-query {{ any; }};
            }};
        """)

    def generate_named_conf_options(self) -> str:
        """Generate bind9 named.conf.options with forwarders."""
        return textwrap.dedent("""\
            options {
                directory "/var/cache/bind";
                recursion yes;
                allow-recursion { any; };
                listen-on { any; };
                forwarders {
                    8.8.8.8;
                    8.8.4.4;
                };
                dnssec-validation auto;
            };
        """)


# ============================================================================
# WEB APPLICATION CONFIGURATION GENERATOR
# ============================================================================

class WebAppConfigGenerator:
    """Generates nginx configuration and HTML landing pages."""

    def __init__(self, domain: str, customer_name: str, applications: List[Dict] = None):
        self.domain = domain
        self.customer_name = customer_name
        self.applications = applications or DEFAULT_APPLICATIONS

    def generate_nginx_site_config(self) -> str:
        """Generate nginx site configuration with SSL vhosts."""
        server_blocks = []

        # Default server block for the root domain
        server_blocks.append(textwrap.dedent(f"""\
            server {{
                listen 80 default_server;
                listen [::]:80 default_server;
                listen 443 ssl default_server;
                listen [::]:443 ssl default_server;
                server_name {self.domain};

                ssl_certificate /opt/certs.{self.domain}/server.crt;
                ssl_certificate_key /opt/certs.{self.domain}/server.key;

                root /var/www/{self.domain};
                index index.html;

                location / {{
                    try_files $uri $uri/ =404;
                }}
            }}
        """))

        # Per-application vhost blocks
        for app in self.applications:
            fqdn = f"{app['subdomain']}.{self.domain}"
            server_blocks.append(textwrap.dedent(f"""\
                server {{
                    listen 80;
                    listen [::]:80;
                    listen 443 ssl;
                    listen [::]:443 ssl;
                    server_name {fqdn};

                    ssl_certificate /opt/certs.{self.domain}/server.crt;
                    ssl_certificate_key /opt/certs.{self.domain}/server.key;

                    root /var/www/{fqdn};
                    index index.html;

                    location / {{
                        try_files $uri $uri/ =404;
                    }}
                }}
            """))

        return "\n".join(server_blocks)

    def generate_landing_page(self, app: Dict) -> str:
        """Generate an HTML landing page for a specific application."""
        fqdn = f"{app['subdomain']}.{self.domain}"
        color = app.get('color', '#2196F3')
        name = app['name']
        desc = app.get('description', '')
        category = app.get('category', '')

        return textwrap.dedent(f"""\
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{name} - {self.customer_name}</title>
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: linear-gradient(135deg, {color}22 0%, {color}11 100%);
                        min-height: 100vh; display: flex; align-items: center;
                        justify-content: center;
                    }}
                    .container {{
                        background: white; border-radius: 16px; padding: 48px;
                        box-shadow: 0 4px 24px rgba(0,0,0,0.1); max-width: 600px;
                        width: 90%; text-align: center;
                    }}
                    .icon {{
                        width: 80px; height: 80px; border-radius: 20px;
                        background: {color}; margin: 0 auto 24px;
                        display: flex; align-items: center; justify-content: center;
                        font-size: 36px; color: white;
                    }}
                    h1 {{ color: #333; margin-bottom: 8px; font-size: 28px; }}
                    .category {{ color: {color}; font-size: 14px; font-weight: 600;
                        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }}
                    .description {{ color: #666; font-size: 16px; line-height: 1.6; margin-bottom: 24px; }}
                    .info {{
                        background: #f5f5f5; border-radius: 8px; padding: 16px;
                        font-size: 13px; color: #888;
                    }}
                    .info strong {{ color: #555; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon">&#9679;</div>
                    <h1>{name}</h1>
                    <div class="category">{category}</div>
                    <p class="description">{desc}</p>
                    <div class="info">
                        <strong>Host:</strong> {fqdn}<br>
                        <strong>Organization:</strong> {self.customer_name}<br>
                        <strong>Environment:</strong> POV Demo
                    </div>
                </div>
            </body>
            </html>
        """)

    def generate_root_page(self) -> str:
        """Generate the root domain landing page with app directory."""
        app_cards = []
        for app in self.applications:
            fqdn = f"{app['subdomain']}.{self.domain}"
            color = app.get('color', '#2196F3')
            app_cards.append(
                f'<a href="https://{fqdn}" class="app-card" '
                f'style="border-left-color: {color};">'
                f'<div class="app-name">{app["name"]}</div>'
                f'<div class="app-cat">{app.get("category", "")}</div>'
                f'<div class="app-url">{fqdn}</div></a>'
            )
        cards_html = "\n            ".join(app_cards)

        return textwrap.dedent(f"""\
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{self.customer_name} - Application Portal</title>
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: #f0f2f5; color: #333;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
                        color: white; padding: 48px 24px; text-align: center;
                    }}
                    .header h1 {{ font-size: 32px; margin-bottom: 8px; }}
                    .header p {{ opacity: 0.8; font-size: 16px; }}
                    .grid {{
                        max-width: 1000px; margin: 32px auto; padding: 0 24px;
                        display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                        gap: 16px;
                    }}
                    .app-card {{
                        background: white; border-radius: 8px; padding: 20px;
                        text-decoration: none; color: inherit;
                        border-left: 4px solid #ccc;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        transition: transform 0.2s, box-shadow 0.2s;
                    }}
                    .app-card:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    }}
                    .app-name {{ font-weight: 600; font-size: 16px; margin-bottom: 4px; }}
                    .app-cat {{ font-size: 12px; color: #888; text-transform: uppercase;
                        letter-spacing: 0.5px; margin-bottom: 8px; }}
                    .app-url {{ font-size: 13px; color: #1565C0; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{self.customer_name}</h1>
                    <p>Application Portal &mdash; POV Environment</p>
                </div>
                <div class="grid">
                    {cards_html}
                </div>
            </body>
            </html>
        """)


# ============================================================================
# PKI CERTIFICATE GENERATOR
# ============================================================================

class PKICertGenerator:
    """Generates OpenSSL shell script for full PKI hierarchy."""

    def __init__(
        self,
        domain: str,
        customer_name: str,
        applications: List[Dict] = None,
        employees: List[Dict] = None,
        pki_options: Dict[str, bool] = None,
        trust_devices: List[Dict] = None,
    ):
        self.domain = domain
        self.customer_name = customer_name
        self.applications = applications or DEFAULT_APPLICATIONS
        self.employees = employees or DEFAULT_EMPLOYEES
        self.pki_options = pki_options or {
            'server_cert': True,
            'device_certs': True,
            'user_certs': True,
            'decryption_ca': True,
        }
        self.trust_devices = trust_devices or []
        self.cert_dir = f"/opt/certs.{domain}"

    def generate_pki_script(self) -> str:
        """Generate the complete PKI hierarchy creation script."""
        sections = [
            self._header(),
            self._root_ca(),
        ]

        if self.pki_options.get('server_cert', True):
            sections.append(self._server_intermediate_ca())
            sections.append(self._server_cert())

        if self.pki_options.get('device_certs', True):
            sections.append(self._device_intermediate_ca())
            sections.append(self._device_certs())

        if self.pki_options.get('user_certs', True):
            sections.append(self._user_intermediate_ca())
            sections.append(self._user_certs())

        if self.pki_options.get('decryption_ca', True):
            sections.append(self._decryption_intermediate_ca())

        sections.append(self._fix_permissions())

        return "\n".join(sections)

    def _header(self) -> str:
        return textwrap.dedent(f"""\
            #!/bin/bash
            # PKI Certificate Hierarchy for {self.customer_name}
            # Domain: {self.domain}
            # Generated by PA Config Lab POV Builder

            set -e
            CERT_DIR="{self.cert_dir}"
            mkdir -p "$CERT_DIR/{{root,server-ca,device-ca,user-ca,decryption-ca}}"
            cd "$CERT_DIR"
        """)

    def _root_ca(self) -> str:
        cn = f"{self.customer_name} Root CA"
        return textwrap.dedent(f"""\

            # =============================================
            # ROOT CA (RSA 4096, 10 year)
            # =============================================
            openssl genrsa -out root/root-ca.key 4096

            openssl req -new -x509 -days 3650 -sha256 \\
                -key root/root-ca.key \\
                -out root/root-ca.crt \\
                -subj "/C=US/ST=California/L=Santa Clara/O={self.customer_name}/OU=Security/CN={cn}"

            # Root CA serial and database
            echo "01" > root/serial
            touch root/index.txt
        """)

    def _intermediate_ca_section(self, name: str, dir_name: str, cn: str) -> str:
        """Generate an intermediate CA section."""
        return textwrap.dedent(f"""\

            # =============================================
            # {name.upper()} INTERMEDIATE CA (RSA 4096, 5 year)
            # =============================================
            openssl genrsa -out {dir_name}/{dir_name}.key 4096

            openssl req -new -sha256 \\
                -key {dir_name}/{dir_name}.key \\
                -out {dir_name}/{dir_name}.csr \\
                -subj "/C=US/ST=California/L=Santa Clara/O={self.customer_name}/OU=Security/CN={cn}"

            # Sign with Root CA
            openssl x509 -req -days 1825 -sha256 \\
                -in {dir_name}/{dir_name}.csr \\
                -CA root/root-ca.crt \\
                -CAkey root/root-ca.key \\
                -CAserial root/serial \\
                -out {dir_name}/{dir_name}.crt \\
                -extfile <(cat <<INTEOF
            basicConstraints = critical, CA:TRUE, pathlen:0
            keyUsage = critical, keyCertSign, cRLSign
            subjectKeyIdentifier = hash
            authorityKeyIdentifier = keyid:always, issuer
            INTEOF
            )

            # Create chain file
            cat {dir_name}/{dir_name}.crt root/root-ca.crt > {dir_name}/{dir_name}-chain.crt

            echo "01" > {dir_name}/serial
            touch {dir_name}/index.txt
        """)

    def _server_intermediate_ca(self) -> str:
        cn = f"{self.customer_name} Server Signing CA"
        return self._intermediate_ca_section("Server Signing", "server-ca", cn)

    def _server_cert(self) -> str:
        # Build SAN list
        san_entries = [f"DNS:*.{self.domain}", f"DNS:{self.domain}"]
        for app in self.applications:
            san_entries.append(f"DNS:{app['subdomain']}.{self.domain}")
        san_string = ",".join(san_entries)

        cn = f"*.{self.domain}"
        return textwrap.dedent(f"""\

            # Server Certificate (RSA 2048, 1 year, wildcard + SAN)
            openssl genrsa -out server.key 2048

            openssl req -new -sha256 \\
                -key server.key \\
                -out server.csr \\
                -subj "/C=US/ST=California/L=Santa Clara/O={self.customer_name}/CN={cn}"

            openssl x509 -req -days 365 -sha256 \\
                -in server.csr \\
                -CA server-ca/server-ca.crt \\
                -CAkey server-ca/server-ca.key \\
                -CAserial server-ca/serial \\
                -out server.crt \\
                -extfile <(cat <<SRVEOF
            basicConstraints = CA:FALSE
            keyUsage = critical, digitalSignature, keyEncipherment
            extendedKeyUsage = serverAuth
            subjectAltName = {san_string}
            subjectKeyIdentifier = hash
            authorityKeyIdentifier = keyid, issuer
            SRVEOF
            )

            # Full chain for nginx
            cat server.crt server-ca/server-ca.crt root/root-ca.crt > server-fullchain.crt
        """)

    def _device_intermediate_ca(self) -> str:
        cn = f"{self.customer_name} Device Signing CA"
        return self._intermediate_ca_section("Device Signing", "device-ca", cn)

    def _device_certs(self) -> str:
        lines = ["\n# Device Certificates"]
        devices = self.trust_devices or [{'name': 'ServerVM'}]
        for device in devices:
            dev_name = device.get('name', 'device').lower().replace(' ', '-')
            cn = f"{dev_name}.{self.domain}"
            lines.append(textwrap.dedent(f"""\
                # Device cert: {dev_name}
                openssl genrsa -out device-ca/{dev_name}.key 2048
                openssl req -new -sha256 \\
                    -key device-ca/{dev_name}.key \\
                    -out device-ca/{dev_name}.csr \\
                    -subj "/C=US/ST=California/O={self.customer_name}/OU=Devices/CN={cn}"
                openssl x509 -req -days 365 -sha256 \\
                    -in device-ca/{dev_name}.csr \\
                    -CA device-ca/device-ca.crt \\
                    -CAkey device-ca/device-ca.key \\
                    -CAserial device-ca/serial \\
                    -out device-ca/{dev_name}.crt \\
                    -extfile <(cat <<DEVEOF
                basicConstraints = CA:FALSE
                keyUsage = critical, digitalSignature, keyEncipherment
                extendedKeyUsage = clientAuth
                subjectKeyIdentifier = hash
                authorityKeyIdentifier = keyid, issuer
                DEVEOF
                )
            """))
        return "\n".join(lines)

    def _user_intermediate_ca(self) -> str:
        cn = f"{self.customer_name} User Signing CA"
        return self._intermediate_ca_section("User Signing", "user-ca", cn)

    def _user_certs(self) -> str:
        lines = ["\n# User Certificates"]
        for emp in self.employees:
            email = f"{emp['email_prefix']}@{self.domain}"
            cn = emp['name']
            safe_name = emp['email_prefix']
            lines.append(textwrap.dedent(f"""\
                # User cert: {cn}
                openssl genrsa -out user-ca/{safe_name}.key 2048
                openssl req -new -sha256 \\
                    -key user-ca/{safe_name}.key \\
                    -out user-ca/{safe_name}.csr \\
                    -subj "/C=US/ST=California/O={self.customer_name}/OU={emp['department']}/CN={cn}/emailAddress={email}"
                openssl x509 -req -days 365 -sha256 \\
                    -in user-ca/{safe_name}.csr \\
                    -CA user-ca/user-ca.crt \\
                    -CAkey user-ca/user-ca.key \\
                    -CAserial user-ca/serial \\
                    -out user-ca/{safe_name}.crt \\
                    -extfile <(cat <<USREOF
                basicConstraints = CA:FALSE
                keyUsage = critical, digitalSignature, keyEncipherment
                extendedKeyUsage = clientAuth, emailProtection
                subjectAltName = email:{email}
                subjectKeyIdentifier = hash
                authorityKeyIdentifier = keyid, issuer
                USREOF
                )
            """))
        return "\n".join(lines)

    def _decryption_intermediate_ca(self) -> str:
        cn = f"{self.customer_name} Decryption CA"
        return self._intermediate_ca_section("Decryption Signing", "decryption-ca", cn)

    def _fix_permissions(self) -> str:
        return textwrap.dedent(f"""\

            # Fix permissions
            chmod 600 "$CERT_DIR"/**/*.key
            chmod 644 "$CERT_DIR"/**/*.crt
            echo "PKI hierarchy generation complete at $CERT_DIR"
        """)


# ============================================================================
# CLOUD-INIT BUILDER
# ============================================================================

class CloudInitBuilder:
    """Combines DNS, webapp, and PKI into a single cloud-init script."""

    def __init__(
        self,
        domain: str,
        customer_name: str,
        server_ip: str,
        applications: List[Dict] = None,
        employees: List[Dict] = None,
        pki_options: Dict[str, bool] = None,
        trust_devices: List[Dict] = None,
    ):
        self.domain = domain
        self.customer_name = customer_name
        self.server_ip = server_ip
        self.applications = applications or DEFAULT_APPLICATIONS
        self.employees = employees or DEFAULT_EMPLOYEES
        self.pki_options = pki_options or {
            'server_cert': True,
            'device_certs': True,
            'user_certs': True,
            'decryption_ca': True,
        }
        self.trust_devices = trust_devices or []

    def build_cloud_init(self) -> str:
        """Build the complete cloud-init bash script."""
        dns_gen = DNSConfigGenerator(self.domain, self.server_ip, self.applications)
        web_gen = WebAppConfigGenerator(self.domain, self.customer_name, self.applications)
        pki_gen = PKICertGenerator(
            self.domain, self.customer_name, self.applications,
            self.employees, self.pki_options, self.trust_devices,
        )

        # Escape content for heredocs
        zone_file = dns_gen.generate_zone_file()
        named_conf_local = dns_gen.generate_named_conf_local()
        named_conf_options = dns_gen.generate_named_conf_options()
        nginx_config = web_gen.generate_nginx_site_config()
        pki_script = pki_gen.generate_pki_script()
        root_page = web_gen.generate_root_page()

        # Build landing page deployment commands
        landing_pages_cmds = []
        for app in self.applications:
            fqdn = f"{app['subdomain']}.{self.domain}"
            page_content = web_gen.generate_landing_page(app)
            landing_pages_cmds.append(
                f'mkdir -p /var/www/{fqdn}\n'
                f'cat > /var/www/{fqdn}/index.html << \'APPEOF\'\n'
                f'{page_content}\n'
                f'APPEOF'
            )
        landing_pages_block = "\n\n".join(landing_pages_cmds)

        script = textwrap.dedent(f"""\
            #!/bin/bash
            # Cloud-Init Script for {self.customer_name} ServerVM
            # Domain: {self.domain}
            # Generated by PA Config Lab POV Builder
            set -e

            export DEBIAN_FRONTEND=noninteractive

            # ===== Step 1: Install packages =====
            apt-get update -qq
            apt-get install -y -qq bind9 bind9utils nginx openssl > /dev/null

            # ===== Step 2: Generate PKI certificates =====
            {pki_script}

            # ===== Step 3: Configure bind9 DNS =====
            mkdir -p /etc/bind/zones

            cat > /etc/bind/zones/db.{self.domain} << 'ZONEEOF'
            {zone_file}
            ZONEEOF

            cat > /etc/bind/named.conf.local << 'NLEOF'
            {named_conf_local}
            NLEOF

            cat > /etc/bind/named.conf.options << 'NOEOF'
            {named_conf_options}
            NOEOF

            # ===== Step 4: Configure nginx =====
            # Remove default site
            rm -f /etc/nginx/sites-enabled/default

            cat > /etc/nginx/sites-available/{self.domain} << 'NGEOF'
            {nginx_config}
            NGEOF

            ln -sf /etc/nginx/sites-available/{self.domain} /etc/nginx/sites-enabled/

            # ===== Step 5: Deploy landing pages =====
            mkdir -p /var/www/{self.domain}
            cat > /var/www/{self.domain}/index.html << 'ROOTEOF'
            {root_page}
            ROOTEOF

            {landing_pages_block}

            # ===== Step 6: Restart services =====
            systemctl restart bind9
            systemctl restart nginx
            systemctl enable bind9
            systemctl enable nginx

            echo "ServerVM services configuration complete for {self.domain}"
        """)

        return script
