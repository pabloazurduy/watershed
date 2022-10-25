# watershed
Watershed Challenge

you can clone and read the results directly from `Challenge.html` or `Challenge.ipynb`.
### Files and directories: 

1. `Challenge.ipynb` : The full assignment notebook. There is also an export in HTML `Challenge.html`
2. `Challenge.html`: A copy of the exported notebook, this works as a backup of the outputs, it has links to some images on the repo so please clone and open it on the original directory.
3. `anomaly_plots/`: This directory has the plot exportation of the anomaly detection algorithm implemented in `anomaly.py` these images are named after the `<variable>_<basin_id>` so you can check the anomaly detection algorithm.  
4. `anomaly.py`: an anomaly detection implementation, this module will export the results in the plots folder but also a `csv` with all the flags (`anomaly_flag.csv.gz`). This module uses `multiprocessing`
5. `anomaly_flag.csv.gz`: Compressed csv file with the `anomaly.py` script result. 
7. `others.py`: A module with some util implementations
8. `requirements.txt`: The python package description used in this project


### Setup and Execution 

To execute `Challenge.ipynb` install the packages requires on the `requirements.txt`.

You can also re-run the anomaly detection script (`anomaly.py`) but that takes a long time to execute (depending on the number of cores)

### **Note**:
Some files were compressed to upload them to the repository; `anomaly_flag.csv.gz` and the plots in `anomaly_plots/`. There is no need to uncompress them, but if you run the `anomaly.py` script again it will generate the uncompressed files 