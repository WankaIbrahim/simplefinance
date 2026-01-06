# SimpleFinance
## COMP3207 Cloud App - Group Coursework

Last update: `05/01/2026`

File Structure:
```
> backend
-> shared_code - contains the code for the User and Group objects
-> tests
--> test_functions.py - contains the unit tests for the azure function app
-> examples.py - provides example usage of the azure function app
-> function.app - contains the main azure function app logic
```

```
> frontend

-> public - additional vue logic
--> game.js
--> main.css
--> header.css

-> src - put all logic required for the front-end here
--> azureModel.js - connection and requests that will go to the Azure server go here

-> views - put all html in here
--> display.ejs - holds the login and welcome pages (localhost:8080/display)
--> group-view.ejs - view for a spending group (localhost:8080/group-view)
--> header.ejs - website header (nav menu) - imported on all pages
--> footer.ejs - website footer - imported on all pages
--> welcome.ejs - not used (localhost:8080/)
--> login.ejs - not used

-> app.js - server setup
```

To run the back-end server locally:
```
pip install -r requirements.txt
```
then
```
func start
```


To run the front-end server locally:
```
npm install
```

and then

```
npm run
```