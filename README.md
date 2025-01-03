# DMD Downloader

An automated tool to download and extract DM+D (Dictionary of Medicines and Devices) releases from the NHS TRUD service.

---

## Setup

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd <repository_directory>

2. **Virtual Environment**:
    pipenv install
    pipenv shell 
3. **Install dependencies**:
    pipenv run pip install -r requirements.txt
4. **.env**:
    TRUD_API_KEY=your_api_key_here
5. **Manual Run**:
    python your_script.py
6. **RUN SHELL**:
    chmod +x run_dmd_download.sh
7. **Schedule Script**:
    for linux -> crontab -e
    opening crontab -e 
    use this trigger -> 
**Daily at 2 AM**
0 2 * * * /path/to/run_dmd_download.sh

**Weekly on Monday at 3 AM**
0 3 * * 1 /path/to/run_dmd_download.sh

**Monthly on the 1st at 4 AM**
0 4 1 * * /path/to/run_dmd_download.sh






