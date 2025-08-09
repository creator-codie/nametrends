## Deployment guide for NameTrends

Follow these steps to put the NameTrends site online using only free tools:

1. **Create a public GitHub repository.** Give it a name such as `nametrends`.
2. **Upload the project files.** Upload everything inside the `NameTrends_autonomous_site_v3` folder to the root of your new repository. Make sure that the directory structure (including `.github/workflows`) remains intact.
3. **Enable GitHub Actions.** Navigate to the `Actions` tab of your repository. The workflow named *Publish site* should appear. Click **Run workflow** to trigger the first build.
4. **Configure GitHub Pages.** In **Settings → Pages**, set the source to **GitHub Actions**. The site will be served from the `gh-pages` branch created by the workflow. Note the URL provided (typically `https://<your‑username>.github.io/<repo>`).
5. *(Optional)* **Add your Amazon affiliate ID.** Open `config.json` and enter your Amazon Associates tag under the `"amazon_tag"` field. When present, product links on the site will automatically include your affiliate ID.
6. *(Optional)* **Submit your sitemap to search engines.** After the first publish completes, a `sitemap.xml` will be available at the root of the site. Submit this to Google Search Console and Bing Webmaster Tools to speed up indexing.

Once configured, the GitHub Action runs daily (at about 10:20 AM America/Toronto time) to fetch fresh SSA data and update the pages. Because the workflow uses the `keep_files` option, new pages are added while old content remains intact, allowing the site to grow over time with no manual intervention.
