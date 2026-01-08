# COMP3207 Cloud App - Group Coursework
## SimpleFinance - Group L

### How to Run Localy
When you download the folder locally, you should have the following file structure:

```bash
simplefinance
|- backend
|- frontend
```

Folder `backend` contains the Azure development server that will handle the calls to the Azure API.
Folder `frontend` contains the Vue and Express.js server that will handle the interaction between the user and the backend.

Before you can run the backend and frontend, you must have the following installed:

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) installed
- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) installed
- A project created in the [Google Cloud Console](https://console.cloud.google.com/)

When inside `..\simplefinance`, run the backend localy with the following commands:

```bash
cd backend
pip install -r requirements.txt
func start
```

When inside `..\simplefinance`, run the frontend localy with the following commands:

```bash
cd frontend
npm install
npm start
```

You can also run `run.bat` inside `..\simplefinance\` - it will automatically install all dependencies.

```
.\run.bat
```

### How to Deploy on Azure and Google Cloud
#### Azure Deployment
1. Login to Azure - `az login`
2. 
3.
4.

#### Google Cloud Deployment 