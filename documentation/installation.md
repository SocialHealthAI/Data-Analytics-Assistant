## Installation
This project uses Docker Compose to define, build, and run multiple interdependent services in a single environment. Each service runs in its own container, but all share a common Docker network for communication.

##### Prerequisites
Before getting started, ensure you have the following installed:
* Docker Engine and the Docker Compose plugin
* Git (for cloning this repository)
* At least 8 GB of RAM and 10 GB of free disk space

If Docker is not yet installed on your system, follow the official documentation for your platform:

🪟 Windows	[Install Docker Desktop on Windows](https://docs.docker.com/desktop/install/windows-install/)
🍎 macOS	[Install Docker Desktop on Mac](https://docs.docker.com/desktop/install/mac-install/)
🐧[ Linux	Install Docker Engine on Linux](https://docs.docker.com/engine/install/)

Once the Git repository is cloned, navigate to the repo directory.

##### Starting the Assistant
The default setup supplies the database and data dictionary and pulls images from DockerHub.

Set your OpenAI key in the **.env** file:

~~~
# Keys
OPENAI_API_KEY=sk-....
TAVILY_API_KEY=tvly-...
~~~
The Tavily key is optional. If not provided, the search_tool will not be enabled.

To build and start the containers:
```
docker-compose up
```
To start an instance of the assistant, see the **Usage** section above.

##### Tailoring the Configuration
The **.env** file has parameters that can be adjusted for your configuration.  You must update the OpenAI key but the Tavily key is optional:
~~~
# Keys
OPENAI_API_KEY=sk-....
TAVILY_API_KEY=tvly-...
~~~
The **da_assistant** and **da_assistant_etl** containers expose ports to your host for use with browsers. If you need to update the ports:
~~~
# Host ports (change as needed)
ASSISTANT_HOST_PORT=8052
ETL_HOST_PORT=8888
~~~
The other containers use the isolated docker compose network.

If you want to expose the **da_assistant** and **da_assistant_etl** containers to external hosts (e.g., another device on your network), change their bind addresses to `0.0.0.0`.\
Otherwise, `127.0.0.1` will restrict access to your local machine
~~~
# Host bind for published services
ASSISTANT_BIND=127.0.0.1
ETL_BIND=127.0.0.1
~~~ 

#### Building Images
You can use Docker to build images by setting the image names as follows:
```
# Image names (set to registry images to pull - otherwise local tags used)
ASSISTANT_IMAGE=da-assistant:local
ETL_IMAGE=da-assistant-etl:local
MCP_IMAGE=da-assistant-osm-mcp:local
DB_IMAGE=da-assistant-db:local
```
You will need additional storage for the Docker build cache.

To build images and containers and start containers use docker compose:
```
docker-compose up
```

