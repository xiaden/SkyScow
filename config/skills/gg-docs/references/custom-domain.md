# Configure, verify, and retire a custom domain

Point a GitHub Pages site at a custom domain, verify and secure it, and clean up
DNS records safely on decommission to prevent takeover.

## Sections
- Add the domain to the site first
- Verify your domain
- Subdomains (CNAME)
- Apex domains (A/AAAA or ALIAS/ANAME)
- HTTPS provisioning
- DNS cleanup and takeover prevention
- Fact stamps

## Add the domain to the site first
Configure the custom domain in the repository Pages settings (or via the Pages
REST API) **before** adding DNS records with your provider. Configuring DNS first,
without adding the domain to GitHub, lets someone else host a site on one of your
subdomains. A `CNAME` file in the repository does not add or remove a custom
domain automatically: it is created by saving a branch-source domain in settings,
and for Actions-source sites it is ignored and not required.

## Verify your domain
Verify the custom domain for your account before (or while) adding it. Verification
prevents other GitHub users from using your domain with their repositories and
reduces takeover risk.

## Subdomains (CNAME)
- Supported: a `www` subdomain or a custom subdomain such as `blog.example.com`.
- Configure a `CNAME` record pointing the subdomain at the site's default domain
  (`<user>.github.io` or `<org>.github.io`), without the repository name.
- `www` subdomains are the most stable because they are not affected by changes to
  the IP addresses of GitHub's servers. Setting up `www` alongside an apex domain
  is recommended for HTTPS.

## Apex domains (A/AAAA or ALIAS/ANAME)
- An apex domain (for example `example.com`) is configured with an `A`, `AAAA`,
  `ALIAS`, or `ANAME` record. Point `A`/`AAAA` records at the four GitHub Pages IP
  addresses, or point an `ALIAS`/`ANAME` at the site's default domain.
- A `CNAME` cannot be used at the apex; use `A`/`AAAA` or `ALIAS`/`ANAME`.
- GitHub Pages automatically redirects between the apex and `www` variants when
  both are configured correctly.

## HTTPS provisioning
Custom domains are served over HTTPS; provisioning a certificate can take time. The
**Enforce HTTPS** option can take up to 24 hours before it becomes available. Treat
HTTPS provisioning as a delayed operation and re-check before relying on it.

## DNS cleanup and takeover prevention
- If the site is disabled but a custom domain is still configured, the domain is at
  risk of takeover: someone can host a site on one of your subdomains.
- When disabling, changing, or decommissioning a Pages site, update or remove the
  custom domain in repository settings **and** remove the DNS records at your
  provider.
- Do not use wildcard DNS records such as `*.example.com`: they create an immediate
  takeover risk even if you verify the domain (verifying `example.com` still leaves
  other names covered by the wildcard available to others).
- Removing the custom domain from the account's user/org site also removes the
  default custom domain applied to its project sites.

## Fact stamps
https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/about-custom-domains-and-github-pages | checked 2026-08-28 | re-check on custom-domain or DNS behavior change
https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site | checked 2026-08-28 | re-check on custom-domain or DNS behavior change
https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages | checked 2026-08-28 | re-check on domain-verification behavior change
https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https | checked 2026-08-28 | re-check on Pages HTTPS behavior change
https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site | checked 2026-08-28 | re-check on Pages publishing-source change
