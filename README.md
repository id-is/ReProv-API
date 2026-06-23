
  

# ReProv-API

This repository is an API-based solution enabling users to register and execute workflows seamlessly by integrating with the [REANA](https://reanahub.io/) execution system. It also offers the capability to capture and visualize data provenance of the workflow executions, based on the [W3C-PROV](https://www.w3.org/TR/prov-o/) standard.

The project consists of three key components:
 - [FastAPI](https://fastapi.tiangolo.com/): Core component enabling RESTful API interactions with the platform.
- [Keycloak](https://www.keycloak.org/): Authentication and access control system ensuring secure user authentication and user grouping
- [MySQL Database](https://www.mysql.com/): Database system serving as the backend for efficient data storage and retrieval.

All three components are deployed in a **dockerized** environment in order to ensure *scalability*, *portability*, and *ease of management*.

This work assumes a platform and core components in line with the architecture specified as part of the HEurope project [AI4Europe](https://cordis.europa.eu/project/id/101070000). 



## Key Features

 - User authentication using keycloak
 - Workflow registration ([CWL](https://www.commonwl.org/) workflows are currently supported).
 - Integration with REANA system to execute previously registered workflows.
 - [CRUD](https://www.codecademy.com/article/what-is-crud) operations both for registered and executed workflows.
 - Data provenance for workflows executed within the REANA framework.
 - Visualization of data provenance by generating graph-based PNG representations, allowing for clear and intuitive 
exploration of workflow dependencies and data flow.
 - Export of provenance as [W3C PROV-JSON](https://www.w3.org/submissions/prov-json/).
 - Failure-aware provenance: failed steps are recorded with their status, exit code, and error message.
 - Per-step resource-usage capture (CPU time, peak memory, disk I/O).
 - Linking workflow inputs to datasets in the [AI-on-Demand](https://aiod.eu) catalogue via the `valueFromPlatform` keyword.
 - A [Python SDK](sdk/README.md) for programmatic access to the API.


## Documentation & examples

 - [USAGE.md](USAGE.md) — end-to-end walkthrough (authenticate → register → execute → capture provenance), with `curl` and SDK examples.
 - [examples/](examples/README.md) — ready-to-run example CWL workflows (MNIST, a deliberately failing variant, an AIoD-linked variant, and a larger heatwave-prediction pipeline).
 - [sdk/](sdk/README.md) — the Python SDK.
 - Interactive API docs (OpenAPI/Swagger) are served at `/docs` once the API is running.


## Prerequisites
- `Linux / macOS`
- `Python version >= 3.10 (preferably 3.10)`
- `docker version >= 24.0.7`
- `docker-compose version >= 1.29.2`
-  Access to an operational *REANA* instance. You will need *URL* of the service along with the corresponding *ACCESS TOKEN* . 

## Local Installation
In order to install the platform locally, follow the steps outlined below 

#### Clone the repository
	
    git clone https://github.com/id-is/ReProv-API

#### Move into the local directory and create the new virtual environment

    cd ReProv-API

#### Create a *.env* file
    touch .env
    
#### Add values to the `.env` file
The values you add to the `.env` file are the ones that should be defined in order to run the application. Each value should follow the format `KEY=VALUE`, where `KEY` is the name of the environment variable and `VALUE` is its corresponding value.

Using your favorite editor, you have to adjust the following variables based on your system. 
Some things to consider are:
 1. Every environmental variable with the *MYSQL* prefix (**except MYSQL_SERVER**) can be configured as desired.
 2. Every environmental variable with the *KEYCLOAK* prefix (**except KEYCLOAK_ADMIN_USERNAME and KEYCLOAK_ADMIN_PASSWORD) must not be changed**

Note that `KEYCLOAK_CLIENT_SECRET` must have empty value as demonstrated below

    REANA_SERVER_URL=<URL OF REANA INSTANCE>
    REANA_ACCESS_TOKEN=<TOKEN OF REANA INSTANCE>
    
    MYSQL_SERVER=prov-db
    MYSQL_ROOT_PASSWORD=root_password
    MYSQL_DATABASE=prov_db
    MYSQL_USER=user
    MYSQL_PASSWORD=password
    
    KEYCLOAK_SERVER_URL=http://prov-keycloak:8080/
    KEYCLOAK_REALM=prov
    KEYCLOAK_AUTHORIZATION_URL=http://localhost:8080/realms/prov/protocol/openid-connect/auth
    KEYCLOAK_TOKEN_URL=http://localhost:8080/realms/prov/protocol/openid-connect/token
    KEYCLOAK_CLIENT_ID=api
    KEYCLOAK_CLIENT_SECRET=
    KEYCLOAK_ADMIN_USERNAME=admin
    KEYCLOAK_ADMIN_PASSWORD=admin


Create and start all 3 containers using *docker-compose*.

    docker-compose up -d

If you want to delete all 3 containers without deleting the data created
    
    docker-compose down

If you want to delete all 3 containers alongside with the data created

    docker-compose down -v
    
#### If you want to further develop API
Create a new virtual environment

    python -m venv venv
    source venv/bin/activate

#### Install dependencies (this may take a few minutes)

    pip install -r requirements.txt
#### Start keycloak and database

    docker-compose up -d prov-db prov-keycloak
#### Configure .env file again

#### Find the IP addresses of prov-keycloak and prov-db containers

    prov_db_addr = $(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' prov-db)
    prov_keycloak_addr = $(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' prov-keycloak)

#### Change the following variables at .env file

    KEYCLOAK_SERVER_URL=prov_keycloak_addr
    MYSQL_SERVER=prov_db_addr

#### Run Uvicorn Server locally

    cd src
    uvicorn main:app --host=0.0.0.0 --port=8000 --reload --env-file ../.env

Once started, you should be able to

 1.  Visit the REST API at http://localhost:8000/docs 
Instructions for using the API will be provided in the next sections
 3. Visit Keycloak at http://localhost:8080/ . In the current configuration Keylcoak is filled with 5 users and 2 groups. Each user has credentials of the form *useri / passwordi* where i $\in [1,\dots,5]$ (e.g. *user1 / password1*).
 You can have admin access by using the credentials defined above. 




## Usage

#### Authenticate
Fisrt thing that you have to do is authenticate from the API  against Keycloak service. 
You'll find the authentication button located at the top right of the screen.

![screenshot](media/authorize_button.png)

After you click on it, the authentication prompt will be opened. You have to add *api* to *client_id* field as it is demonstrated next.

![screenshot](media/authorize_prompt.png)


Next, click authorize button and you will be redirected to keycloak to fill your credentials. In this example, we are using *user1* for user and *password1* for password.

![screenshot](media/keycloak_prompt.png)


Finally, if the credentials are correct, you are done with the authentication process and the following screen must appear.

![screenshot](media/authorize_response.png)


### Core Components of the API

Core components of our API are organized in the following categories:

 - *Workflow Registry*:  Endpoints that allow registration and management of workflows
 - *Workflow Execution*:  Endpoints that allow execution and monitoring of workflows
 - *Provenance*:  Endpoints that allow capture and visualization of data provenance for previously executed workflows

#### Workflow Registry
Each workflow that is registered in our platform is associated with the following information:

 - *`name`*: User provided name for the new entry in registry
 - *`version`*: User provided version for the new entry in registry
	 -  Note that combination of name and version must be unique
- *`spec_file`*:  Content of workflow specification file (CWL file). Each *`spec_file`* must be organized as following:
	-    Each workflow defined must include a `requirements` section.
	-   The `requirements` section specifies the Docker image  that provides the needed environment for executing the workflow.
  ```yaml
  requirements:
  DockerRequirement:
    dockerPull:
      <DOCKER_IMAGE>  
  ``` 
	- 	The workflow  should consist of CommandLineTools.
    -   `CommandLineTools` should utilize executables either from:
	    -   Previously defined Docker images.
	    -   Linux basic commands available in the execution environment.
		- you can see an example [here](https://github.com/id-is/provenance-examples/blob/master/workflows/mnist/mnist.cwl): 
	- A special feature is the fact that user is allowed to specify inputs for the workflow by using entities that are defined in the AIoD platform using the corresponding URL of the entity. Using the keyword `valueFromPlatform` on the inputs section of the workflow it is possible to have interaction between different workflows. Syntax is presented below:
   ```yaml
  inputs:
  - id: input_file
       type: File
       valueFromPlatform: "{{<URL>}}"  
  ```
  - you can see an example [here](https://github.com/id-is/provenance-examples/blob/master/workflows/mnist-aiod/mnist-aiod.cwl): 
	 
- *`input_file`*: Input file in *YAML* format that allows workflow to use non-default values for its variables.
	- you can see an example [here](https://github.com/id-is/provenance-examples/blob/master/workflows/mnist/mnist.yaml):  


#### Workflow Execution

Each workflow that is executed is associated with the following information:

 - `registry_id`: *ID* from *Workflow Registry* that specifies which workflow will be executed
 - `start_time`: When the workflow execution started 
 - `end_time`: When the workflow execution ended 
 - `status`: Status of the execution
 - *REANA* information:
	 - `reana_id` : ID assigned to the execution by *REANA* system
	-  `reana_name` : Name assigned to the execution by *REANA* system
	 - `reana_run_number` Run number assigned to the execution by *REANA* system. If you execute the same workflow multiple times, `reana_run_number` will be incremented each time by 1.

For each workflow execution, we also capture information for each individual step:
- `name` Name of the step
- `status` Status of the step
- `start_time` When the step started
- `end_time` When the step ended
- `exit_code` Exit code of the step (parsed from REANA logs; `0` when finished)
- `command` The user command executed by the step
- `error_message` Tail of the step logs, populated only when the step `status` is `failed`
- `resource_usage` Per-step resource metrics captured by an injected monitoring wrapper: `cpu_time_seconds`, `memory_peak_mb`, `disk_read_bytes`, `disk_write_bytes`, `backend_job_id`

We additionally record the *execution environment* for each execution (REANA server URL, compute backend, Kubernetes memory limit, and the Docker image taken from the CWL spec).


#### Provenance
Basic components of data provenance are Entities and Activities as described in [W3C-PROV](https://www.w3.org/TR/prov-o/) standard. In order to "map" our workflows with those components we make the following assumptions:
- Every *registered* workflow is an *Entity*.
- Every *execution* of a workflow is an *Activity*.
- Every *execution* of a step of a workflow is an *Activity*.
- Every *activity* used some (0 or more) *entities*.
- Every *activity* generated some (0 or more) *entities*.


### Endpoints
#### Workflow Registry

 - /**workflow_registry**
	 - Method: ***GET***
	 - Description:  Retrieve all workflows that are registered in our platform
	 
	 **Parameters**: None

	**Responses**:	 	 
   |success| code | message | data
   |--|--|--|--|
   | True |200  |Workflows successfully retrieved| JSON containing registered workflows|
   | False |401  |Not authenticated| None|
	<br>

 - /**workflow_registry/{registry_id}**
	- Method: ***GET***
	 - Description:  Retrieve registered workflow with id = {registry_id}
	 
	  **Parameters**:
    |name| type|
     |--|--|
     | *registry_id* | *int*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |Workflow was successfully retrieved| JSON containing registered workflow|
   | False |401  |Not authenticated| None|
   | False |404  |Invalid registry_id| None|
 
 <br>
 
 - **/workflow_registry/register/**
	- Method: ***POST***
	 - Description:  Register a new workflow in the platform
	 
	  **Parameters**:
    |name| type|
    |--|--|
    | *name* | *string*|
    | *version* | *string*|
    | *spec_file* | *File*|
    | *input_file (optional)* | *File*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |New Workflow was successfully registered| JSON containing information <br> about new workflow registered|
   | False |401  |Not authenticated| None|
   | False |400 |Integrity error. Duplicate name and version combination| None|

<br>

- **/workflow_registry/update/{registry_id}**
	 - Method: ***PUT***
	 - Description:   Update workflow with id = {*registry_id*}. This endpoint will only update fields where new values were provided.
	 
	 **Parameters**:
    |name| type|
    |--|--|
    | *registry_id* | *int*|
    | *name (optional)* | *string*|
    | *version (optional)* | *string*|
    | *spec_file (optional)* | *File*|
    | *input_file (optional)* | *File*|

     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |Workflow was succesfully updated| None|
   | False |401  |Not authenticated| None|
   | False |404 |Invalid registry_id| None|

<br>

- **/workflow_registry/delete/{registry_id}**
	 - Method: ***DELETE***
	 - Description:   Delete workflow with id = {*registry_id*}.
	 
	 **Parameters**:
    |name| type|
    |--|--|
    | *registry_id* | *int*|
    
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |Workflow was succesfully deleted| None|
   | False |401  |Not authenticated| None|
   | False |404 |Invalid registry_id| None|

<br>

#### Workflow Execution

- **/workflow_execution/**
	 - Method: ***GET***
	 - Description:   Retrieves every execution that has occurred using a workflow from our registry.
	 
	 **Parameters**: None

    
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |Workflow executions retrieved successfully| JSON containing executed workflows |
   | False |401  |Not authenticated| None|
   	<br>

 - /**workflow_execution/{execution_id}**
	- Method: ***GET***
	 - Description:  Retrieve executed workflow with id = {execution_id}
	 
	  **Parameters**:
    |name| type|
     |--|--|
     | *execution_id* | *int*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |Workflow execution successfully retrieved| JSON containing executed workflow|
   | False |401  |Not authenticated| None|
   | False |404  |Invalid execution_id| None|
    <br>

 - /**workflow_execution/{execution_id}/logs**
	- Method: ***GET***
	 - Description:  Retrieve per-step logs for an execution. Live logs are fetched from *REANA* and enriched with stored step info (`exit_code`, `error_message`, `command`).
	 
	  **Parameters**:
    |name| type|
     |--|--|
     | *execution_id* | *int*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |Logs retrieved successfully| JSON containing per-step logs|
   | False |401  |Not authenticated| None|
   | False |404  |Invalid execution_id| None|
   | False |503  |Failed to fetch logs from REANA| None|
    <br>

 - /**workflow_execution/execute/{registry_id}**
	- Method: ***POST***
	 - Description:  Execute workflow with id = {*registry_id*} by invoking *REANA* system
	 
	  **Parameters**:
    |name| type|
     |--|--|
     | *registry_id* | *int*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |New workflow started| JSON containing information about the execution that has just began|
   | False |401  |Not authenticated| None|
   | False |404  |Invalid registry_id| None|
   | False |404  |Invalid entity id in placeholder | None|
   | False |503 |Problem while creating / running REANA workflow | None|
   <br>

 - /**workflow_execution/delete/**
	- Method: ***DELETE***
	 - Description:  Delete every workflow execution that was associated with *registry_id* OR with a *name* provided by the REANA system
	 
	  **Parameters**:
    |name| type|
     |--|--|
     | *registry_id (optional)* | *int*|
     | *reana_name (optional)* | *str*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |Every workflow associated with {registry_id} / {reana_name} <br> was successfully deleted"| None
   | False |401  |Not authenticated| None|
   | False |403  |Either provide registry_id OR reana_name but not both| None|
   | False |404  |Invalid registry_id / reana_name| None|
   | False |503 |Problem while deleting REANA workflow | None|
      <br>

 - /**workflow_execution/inputs/{execution_id}**
	- Method: ***GET***
	 - Description:  Download input files of a previously executed workflow with the given *execution_id*
	 
	  **Parameters**:
    |name| type|
     |--|--|
     | *execution_id* | *int*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |None| File containing input values|
   | True |200  |Workflow does not have any input values (default were used)| None|
   | False |401  |Not authenticated| None|
   | False |404  |Invalid execution_id| None|
   | False |409 |Workflow must be finished in order to download input files | None|
	<br>
	
 - /**workflow_execution/outputs/{execution_id}**
	- Method: ***GET***
	 - Description:  Download output files of a previously executed workflow with the given *execution_id*
	 
	  **Parameters**:
    |name| type|
     |--|--|
     | *execution_id* | *int*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |None| Zipped file containing output files|
   | False |401  |Not authenticated| None|
   | False |404  |Invalid execution_id| None|
   | False |409 |Workflow must be finished in order to download output files | None|

#### Provenance

- **/provenance/capture/{execution_id}**
	 - Method: ***GET***
	 - Description:   Capture provenance for the workflow execution with id = {*execution_id*}. File relationships (used/generated) are resolved from the CWL spec, and step status, resource usage, and execution environment are recorded. Works for both *finished* and *failed* executions.
	 
	 **Parameters**:
    |name| type|
     |--|--|
     | *execution_id* | *int*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |Provenance captured successfully| JSON summary (`workflow_status`, `total_steps`, `failed_steps`, `has_detailed_provenance`)|
   | False |401  |Not authenticated| None|
   | False |403  |Provenance was captured before| None|
   | False |404 |Invalid execution_id | None|
   | False| 409 | Workflow must be finished or failed in order to capture provenance| None|
   <br>
   
 - **/provenance/draw/{execution_id}**
	 - Method: ***GET***
	 - Description:   Create a graphical representation of provenance for the workflow execution with id = {*execution_id*} by utilizing the [prov](https://pypi.org/project/prov/) module. Failed step nodes are highlighted in red. Provenance must have been captured first via */provenance/capture/{execution_id}*.
	 
	 **Parameters**:
    |name| type|
     |--|--|
     | *execution_id* | *int*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |None| PNG file containing graphical representation of provenance|
   | False |401  |Not authenticated| None|
   | False |404 |Invalid execution_id | None|
   <br>

 - **/provenance/json/{execution_id}**
	 - Method: ***GET***
	 - Description:   Export the captured provenance for the workflow execution with id = {*execution_id*} as a [W3C PROV-JSON](https://www.w3.org/submissions/prov-json/) document. Provenance must have been captured first via */provenance/capture/{execution_id}*.
	 
	 **Parameters**:
    |name| type|
     |--|--|
     | *execution_id* | *int*|
  
     **Responses**:

   |success| code | message | data
   |--|--|--|--|
   | True |200  |None| W3C PROV-JSON document|
   | False |401  |Not authenticated| None|
   | False |404 |Invalid execution_id | None|
   | False |404 |No provenance captured yet. Call /capture/{execution_id} first.| None|

Two example outputs can be seen here:


<img src="media/prov1.png" width="400" height="200"> <img src="media/prov2.png" width="350" height="200">
