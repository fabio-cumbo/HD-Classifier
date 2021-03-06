# Hyperdimensional Computing Classifier
#### Originally forked from [https://github.com/moimani/HD-Permutaion](https://github.com/moimani/HD-Permutaion)

This repository includes some Python 3 utilities to build a Hyperdimensional Computing classification model according to the architecture
originally introduced in [https://doi.org/10.1109/DAC.2018.8465708](https://doi.org/10.1109/DAC.2018.8465708)

The `src/generators` folder contains two Python3 scripts able to create training a test datasets with randomly selected samples from:
- BRCA, KIRP, and THCA DNA-Methylation data from the paper [Classification of Large DNA Methylation Datasets for Identifying Cancer Drivers](https://doi.org/10.1016/j.bdr.2018.02.005) by Fabrizio Celli, Fabio Cumbo, and Emanuel Weitschek;
- Gene-expression quantification and Methylation Beta Value experiments provided by [OpenGDC](https://github.com/fabio-cumbo/OpenGDC/) for all the 33 different types of tumors of the TCGA program.

Due to the size of the datasets, they have not been reported on this repository but can be retrieved from: 
- [ftp://bioinformatics.iasi.cnr.it/public/bigbiocl_dna-meth_data/](ftp://bioinformatics.iasi.cnr.it/public/bigbiocl_dna-meth_data/)
- [http://geco.deib.polimi.it/opengdc/](http://geco.deib.polimi.it/opengdc/) and [https://github.com/fabio-cumbo/OpenGDC/](https://github.com/fabio-cumbo/OpenGDC/)

The `isolet` dataset is part of the original forked version of the repository and it has been maintained in order to provide a simple 
toy model for testing purposes only.

### Usage

The following command will launch the HD classifier on the `isolet` dataset:
```
python hdclass.py --dimensionality 10000 --levels 100 --retrain 10 --pickle ../datasets/isolet/isolet.pkl --verbose
```

List of standard arguments:
```
--dimensionality    - Dimensionality of the HDC model (default 10000)
--levels            - Number of level hypervectors
--retrain           - Number of retraining iterations (default 0)
--stop              - Stop retraining if the error rate does not change (default False)
--dataset           - Path to the dataset file
--fieldsep          - Field separator (default ',')
--training          - Percentage of observations that will be used to train the model. 
                      The remaining percentage will be used to test the classification model (default 80)
--seed              - Seed for reproducing random sampling of the observations in the dataset 
                      and build both the training and test set (default 0)
--pickle            - Path to the pickle file. If specified, both '--dataset', '--fieldsep', 
                      and '--training' parameters are not used
--dump              - Build a summary and log files (default False)
--cleanup           - Delete the classification model as soon as it produces the prediction accuracy (default False)
--nproc             - Number of parallel jobs for the creation of the HD model.
                      This argument is ignored if --spark is enabled (default 1)
--verbose           - Print results in real time (default False)
```

List of arguments to enable backward variable selection:
```
--features          - Path to a file with a single column containing the whole set or a subset of feature
--group             - Minimum and maximum number of features among those specified with the --features argument. 
                      It is equals to the number of features under --features if not specified. 
                      Otherwise, it must be less or equals to the number of features under --features. 
                      Warning: computationally intense! Syntax: min:max
```

List of argument for the execution of the classifier on a Spark distributed environment:
```
--spark             - Build the classification model in a Apache Spark distributed environment
--slices            - Number of threads per block in case --gpu argument is enabled. 
                      This argument is ignored if --spark is enabled
--master            - Master node address
--memory            - Executor memory
```

List of arguments for the execution of the classifier on an NVidia powered GPU:
```
--gpu               - Build the classification model on an NVidia powered GPU. 
                      This argument is ignored if --spark is specified
--tblock            - Number of threads per block in case --gpu argument is enabled. 
                      This argument is ignored if --spark is enabled
```

### Credits

Please credit our work in your manuscript by citing:

1. > Fabio Cumbo, Eleonora Cappelli, and Emanuel Weitschek, "A brain-inspired hyperdimensional computing approach for classifying massive DNA methylation data of cancer", MDPI Algoritms, 2020

2. > Fabio Cumbo and Emanuel Weitschek, "An in-memory cognitive-based hyperdimensional approach to accurately classify DNA-Methylation data of cancer", The 11th International Workshop on Biological Knowledge Discovery from Big Data (BIOKDD'20), Communications in Computer and Information Science, vol 1285. Springer, Cham, 2020 [https://doi.org/10.1007/978-3-030-59028-4_1](https://doi.org/10.1007/978-3-030-59028-4_1)

Do not forget to also cite the following paper from which this works takes inspiration:

1. > Mohsen Imani, Chenyu Huang , Dequian Kong, Tajana Rosing, "Hierarchical Hyperdimensional Computing for Energy Efficient Classification", IEEE/ACM Design Automation Conference (DAC), 2018 [https://doi.org/10.1109/DAC.2018.8465708](https://doi.org/10.1109/DAC.2018.8465708)
