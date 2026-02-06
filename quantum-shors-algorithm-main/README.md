# Shor's algorithm testing framework

# Pre-requisites
- Have installed Python 3.10 or 3.11 at minimum
- Clone this Git repository
- Change to the directory created after cloning the repository
- To work in a virtual environment install **virtualenv**: ```$ python3.11 -m pip install virtualenv```
  - To create a virtual environment execute the following command:  
    ```$ virtualenv -p python3.11 venv```
  - To activate the previous virtual environment created, execute the following command:   
    ```$ source venv/bin/activate```
  - To install the dependencies needed on the virtual environment created execute the following command:  
    ```$ pip install -r requirements.txt```
  - To save your IBM cloud credentials before running the tool you need to save your token inside the file 'account_credentials.py'
    and then run the following command:    
    ```$ python utilities/account_credentials.py```

# Running the tool
In order to run the tool you need to execute the main.py script. You can check the options by running the 
command:    
   ```$ python main.py -h```    
The output of the above command will expose all the available options to run the tool for a factoring a particular
integer number and to configure all the possible options in the transpilation process of the quantum circuit that later
will be executed on a particular backend. There is also the possibility of configuring the options for the chosen sampler
as well as error mitigation techniques.
The file 'config.ini' holds all the fields that can be configured in order to avoid entering them using the command line.

# Running examples
- Factorize number 51:    
  ```$ python main.py -n 51 --config config.ini  --verbose```    
  ```....```    
  ```[2025-05-01 16:43:24.650060] - Sampler job submitted with id: d09rh246rr3g00875z90```    
- The final line of the execution output of the above command will print the job id that needs to be used later to 
retrieve the results and generate the outputs. The following line will retrieve the job results:    
  ```$ python main.py --job-id d09rh246rr3g00875z90 --config config.ini```    

