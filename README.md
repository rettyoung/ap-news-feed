# AP News Top News feed (self-hosted)

GitHub Actions runs `scrape_ap.py` every hour. It reads https://apnews.com/hub/apf-topnews, opens each new article once to get its headline, summary and publish time, and writes a dated RSS feed to `docs/feed.xml`. GitHub Pages serves that file publicly so Blogtrottr can poll it. It uses only the Python standard library, so there's nothing to install, and it's free on a public repo.

## Setup (about 10 minutes)

1. **Create a public repo** on GitHub, e.g. `ap-news-feed`. It must be public for free Pages and unlimited Actions minutes. The repo only contains AP headlines and links.
2. **Upload these files**, keeping the folders: `scrape_ap.py`, `README.md`, `.github/workflows/ap-feed.yml`, `docs/index.html`, `data/seen.json`. You can use *Add file → Upload files* and drag the unzipped folder in. Check that `.github` came along, because some systems hide dot-folders.
3. **Allow the workflow to commit:** Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save.
4. **Run it once:** go to the Actions tab, open *AP News feed*, click **Run workflow**. It should go green and commit `docs/feed.xml`.
5. **Turn on Pages:** Settings → Pages → Source: *Deploy from a branch* → Branch `main`, folder **/docs** → Save.
6. **Your feed URL** is `https://<your-username>.github.io/ap-news-feed/feed.xml`. Check it in the W3C Feed Validator (validator.w3.org/feed). Then subscribe to it in Blogtrottr and delete the old RSSHub and Google News AP subscriptions.

## Notes

- **If AP blocks GitHub's servers,** the run fails with `ERROR fetching ... 403`. GitHub emails you about the failure, and the feed keeps its last items. Nothing can be done from a free host in that case.
- **If AP changes its page layout,** the run fails with `no article links found`. The scraper looks for any link containing `apnews.com/article/`, so small redesigns shouldn't break it.
- **Sports, entertainment, lifestyle and video** links are filtered out (`SKIP` in the script).
- **Dates:** each item uses AP's own publish time when the article page has one. Otherwise it uses the time the scraper first saw it, so every item has a date.
- **Schedule:** hourly at :17 UTC. GitHub may delay scheduled runs by a few minutes, and it pauses schedules on repos with no activity for 60 days. The hourly commits normally count as activity.
- **To change the source,** set `AP_HUB` in the workflow, e.g. `https://apnews.com/hub/business`.
