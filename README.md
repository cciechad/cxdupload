cxdupload script by Chad Simmons

Requires python 3.10 or higher

Dependancies can be resolved via pip(requirements.txt) or Poetry(pyproject.toml)

Uploads a directory or file to Cisco TAC via CXD

usage: cxdupload.py [-h] [-s] [-p {1,2,3,4,5,6,7,8}] -c CASE -t TOKEN (-f FILE | -d DIR) [--version]

Upload files or directories to a TAC case via CXD

options:

  -h, --help            show this help message and exit
  
  -s, --stats           Print detailed stats upon exit
  
  -p {1,2,3,4,5,6,7,8}, --threads {1,2,3,4,5,6,7,8}
                        Number of threads
                        
  -c CASE, --case CASE  Cisco TAC Case #
  
  -t TOKEN, --token TOKEN
                        CXD Token
                        
  -f FILE, --file FILE  A single file to attach
  
  -d DIR, --dir DIR     Directory to attach
  
  --version             show program's version number and exit

Case, token and either file or dir arguments are required
