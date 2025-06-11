# FSA SIM

## Prerequisites
- **Python 3.11+**
- **pip**

## Installation
```bash
git clone https://github.com/cw523-01/fsa_sim
cd fsa_sim
```

# create & activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

# install Python dependencies
```bash
pip install -r requirements.txt
python manage.py migrate
```

### Start the development server
```bash
python manage.py runserver
```
### Access the application
Navigate to http://localhost:8000 in your browser
