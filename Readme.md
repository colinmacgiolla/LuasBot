# Luas Bot
A simple bot for scraping [Luas Service Updates](https://luas.ie/travel-updates/), and posting them to [Mastodon](https://botsin.space/@luas).

## GitHub Actions
### Triggers
The triggers `on:` are both cron (every 10 mins) and `workflow_dispatch`. The dispatch allows the GitHub Action to be manually configured.

### Python Version
For python 3.10, be sure to quote or else it will try to do python 3.1 :(

### Secrets
Github gives you 3 different ways for passing secrets to the script. In this case, an `environment` called Execution is created, and it contains an environmental variable called `MASTODON_TOKEN`. 

In order to use this, the `environment` parameter needs to be configured in the job, and the `env` parameter needs to be specified in the step, to map the GitHub environmental variable to the actual env variable in the execution environment.


## Todo
- [x] Cleanup code
- [x] Add proper logging
- [x] Delta for service updates
- [x] Integrate with GitHub actions/cron
