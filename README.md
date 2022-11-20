# Leave2LiveHackathon
Leave2LiveHackathon submission

### 1. Set up dev environment
```

conda create -n l2l python=3.8
conda activate l2l
pip install -r requirements.txt
brew install tesseract
brew install tesseract-lang # for ukranian, russian languages support
```

### 2. Create .env file
```
API_KEY=<BOTFATHER_TOKEN>
GM_API_KEY=<GOOGLE_API_KEY>
DB_URI=<MONGO_URL>
DB_NAME=<DB_NAME>
```