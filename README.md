# certbot_dns_aa

This is a plugin for certbot to implement a DNS-01 challenge for Andrews and Arnold. As Andrews and Arnold don't have an API, it makes use of Selenium to simulate a browser session and modify DNS records from there.

# Usage

```bash
git clone ...
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install certbot selenium webdriver zope
pip install -e .

export AA_USERNAME="your-aa-username"
export AA_PASSWORD="your-aa-password"

sudo -E .venv/bin/certbot certonly --authenticator dns-aa -d "<your_domain>" -v
```


## To-do

- Add cleanup to acme challenge records