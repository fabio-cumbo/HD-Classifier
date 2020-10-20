import os, random, copy, pickle, warnings
import numpy as np
import multiprocessing as mp
from functools import partial
warnings.filterwarnings("ignore")

baseVal = -1

class HDModel(object):
    #Initializes a HDModel object
    #Inputs:
    #   datasetName; name of the dataset
    #   trainData: training data
    #   trainLabels: training labels
    #   testData: testing data
    #   testLabels: testing labels
    #   D: dimensionality
    #   totalLevel: number of level hypervectors
    #   workdir: working directory
    #   spark: use Spark
    #   gpu: use GPU
    #   nproc: number of parallel jobs 
    #Outputs:
    #   HDModel object
    def __init__(self, datasetName, trainData, trainLabels, testData, testLabels, D, totalLevel, workdir, spark=False, gpu=False, nproc=1):
        if len(trainData) != len(trainLabels):
            print("Training data and training labels are not the same size")
            return
        if len(testData) != len(testLabels):
            print("Testing data and testing labels are not the same size")
            return
        self.datasetName = datasetName
        self.workdir = workdir
        self.trainData = trainData
        self.trainLabels = trainLabels
        self.testData = testData
        self.testLabels = testLabels
        self.D = D
        self.totalLevel = totalLevel
        self.levelList = getlevelList(self.trainData, self.totalLevel)
        self.levelHVs = genLevelHVs(self.totalLevel, self.D)
        self.trainHVs = []
        self.testHVs = []
        self.classHVs = []
        self.spark = spark
        self.gpu = gpu
        self.nproc = nproc

    #Encodes the training or testing data into hypervectors and saves them or
    #loads the encoded traing or testing data that was saved previously
    #Inputs: 
    #   mode: decided to use train data or test data
    #Outputs:
    #   none
    def buildBufferHVs(self, mode):
        if self.spark:
            # Load PySpark on demand
            from pyspark import SparkConf, SparkContext
            # Build a Spark context or use the existing one
            # Spark context must be initialised here (see SPARK-5063)
            config = SparkConf().setAppName( self.datasetName )
            context = SparkContext.getOrCreate( config )

        if mode == "train":
            train_bufferHVs = os.path.join( self.workdir, 'train_bufferHVs_{}'.format( str(self.D) ) )
            if os.path.exists( train_bufferHVs ):
                print("Loading Encoded Training Data")
                if self.spark:
                    # Spark Context is running
                    trainHVs = context.pickleFile( train_bufferHVs )
                else:
                    with open( '{}.pkl'.format( train_bufferHVs ), 'rb' ) as f:
                        self.trainHVs = pickle.load(f)
            else:
                print("Encoding Training Data")
                if self.spark:
                    # Spark Context is running
                    trainHVs = context.parallelize( list( zip( self.trainLabels, self.trainData ) ) )
                    trainHVs.map( lambda label, obs: ( label, EncodeToHV( obs, self.D, self.levelHVs, self.levelList ) ) )
                    trainHVs.saveAsPickleFile( train_bufferHVs )
                else:
                    # Multiprocessing
                    trainHVs = { }
                    with mp.Pool( processes=self.nproc ) as pool:
                        EncodeToHVPartial = partial( EncodeToHV_wrapper, 
                                                     D=self.D, 
                                                     levelHVs=self.levelHVs, 
                                                     levelList=self.levelList )

                        chunks = [ self.trainData[ i: i+self.nproc ] for i in range( 0, len(self.trainData), self.nproc ) ]
                        for cid in range( 0, len( chunks ) ):
                            positions = list( range( cid*len(chunks[ cid ]), (cid*len(chunks[ cid ]))+len(chunks[ cid ]) ) )
                            results = pool.starmap( EncodeToHVPartial, zip( chunks[ cid ], positions ) )
                            for position, vector in results:
                                trainHVs[ position ] = vector
                    self.trainHVs = [ vector for _, vector in sorted( trainHVs.items(), key=lambda item: item[ 0 ] ) ]
                    # Sequential
                    #for index in range(len(self.trainData)):
                    #    self.trainHVs.append(EncodeToHV(np.array(self.trainData[index]), self.D, self.levelHVs, self.levelList))
                    with open( '{}.pkl'.format( train_bufferHVs ), 'wb' ) as f:
                        pickle.dump(self.trainHVs, f)
            if self.spark:
                # Spark Context is running
                self.trainHVs = trainHVs.map( lambda obs: obs[ 1 ] ).collect()
                self.classHVs = trainHVs.reduceByKey( lambda obs1HV, obs2HV: np.add( obs1HV, obs2HV ) ).collectAsMap()
            else:
                self.classHVs = oneHvPerClass(self.trainLabels, self.trainHVs)
        else:
            test_bufferHVs = os.path.join( self.workdir, 'test_bufferHVs_{}'.format( str(self.D) ) )
            if os.path.exists( test_bufferHVs ):
                print("Loading Encoded Testing Data")
                if self.spark:
                    # Spark Context is running
                    self.testHVs = context.pickleFile( test_bufferHVs ).map( lambda obs: obs[ 1 ] ).collect()
                else:
                    with open( '{}.pkl'.format( test_bufferHVs ), 'rb' ) as f:
                        self.testHVs = pickle.load(f)
            else:
                print("Encoding Testing Data")  
                if self.spark:
                    # Spark Context is running
                    testHVs = context.parallelize( list( zip( self.testLabels, self.testData ) ) )
                    testHVs.map( lambda label, obs: ( label, EncodeToHV( obs, self.D, self.levelHVs, self.levelList ) ) )
                    testHVs.saveAsPickleFile( test_bufferHVs )
                    self.testHVs = testHVs.map( lambda obs: obs[ 1 ] ).collect()
                else:
                    # Multiprocessing
                    testHVs = { }
                    with mp.Pool( processes=self.nproc ) as pool:
                        EncodeToHVPartial = partial( EncodeToHV_wrapper, 
                                                     D=self.D, 
                                                     levelHVs=self.levelHVs, 
                                                     levelList=self.levelList )
                    
                        chunks = [ self.testData[ i: i+self.nproc ] for i in range( 0, len(self.testData), self.nproc ) ]
                        for cid in range( 0, len( chunks ) ):
                            positions = list( range( cid*len(chunks[ cid ]), (cid*len(chunks[ cid ]))+len(chunks[ cid ]) ) )
                            results = pool.starmap( EncodeToHVPartial, zip( chunks[ cid ], positions ) )
                            for position, vector in results:
                                testHVs[ position ] = vector
                    self.testHVs = [ vector for _, vector in sorted( testHVs.items(), key=lambda item: item[ 0 ] ) ]
                    # Sequential
                    #for index in range(len(self.testData)):
                    #    self.testHVs.append(EncodeToHV(np.array(self.testData[index]), self.D, self.levelHVs, self.levelList))
                    with open( '{}.pkl'.format( test_bufferHVs ), 'wb' ) as f:
                        pickle.dump(self.testHVs, f)
        
        if self.spark:
            # Stop Spark context
            context.stop()

#Performs the initial training of the HD model by adding up all the training
#hypervectors that belong to each class to create each class hypervector
#Inputs:
#   inputLabels: training labels
#   inputHVs: encoded training data
#Outputs:
#   classHVs: class hypervectors
def oneHvPerClass(inputLabels, inputHVs):
    #This creates a dict with no duplicates
    classHVs = dict()
    for i in range(len(inputLabels)):
        name = inputLabels[i]
        if (name in classHVs.keys()):
            classHVs[name] = np.array(classHVs[name]) + np.array(inputHVs[i])
        else:
            classHVs[name] = np.array(inputHVs[i])
    return classHVs

def inner_product(x, y):
    return np.dot(x,y)  / (np.linalg.norm(x) * np.linalg.norm(y) + 0.0)

#Finds the level hypervector index for the corresponding feature value
#Inputs:
#   value: feature value
#   levelList: list of level hypervector ranges
#Outputs:
#   keyIndex: index of the level hypervector in levelHVs corresponding the the input value
def numToKey(value, levelList):
    if (value == levelList[-1]):
        return len(levelList)-2
    upperIndex = len(levelList) - 1
    lowerIndex = 0
    keyIndex = 0
    while (upperIndex > lowerIndex):
        keyIndex = int((upperIndex + lowerIndex)/2)
        if (levelList[keyIndex] <= value and levelList[keyIndex+1] > value):
            return keyIndex
        if (levelList[keyIndex] > value):
            upperIndex = keyIndex
            keyIndex = int((upperIndex + lowerIndex)/2)
        else:
            lowerIndex = keyIndex
            keyIndex = int((upperIndex + lowerIndex)/2)
    return keyIndex  

#Splits up the feature value range into level hypervector ranges
#Inputs:
#   buffers: data matrix
#   totalLevel: number of level hypervector ranges
#Outputs:
#   levelList: list of the level hypervector ranges
def getlevelList(buffers, totalLevel):
    minimum = buffers[0][0]
    maximum = buffers[0][0]
    levelList = []
    for buffer in buffers:
        localMin = min(buffer)
        localMax = max(buffer)
        if (localMin < minimum):
            minimum = localMin
        if (localMax > maximum):
            maximum = localMax
    length = maximum - minimum
    gap = length / totalLevel
    for lv in range(totalLevel):
        levelList.append(minimum + lv*gap)
    levelList.append(maximum)
    return levelList

#Generates the level hypervector dictionary
#Inputs:
#   totalLevel: number of level hypervectors
#   D: dimensionality
#Outputs:
#   levelHVs: level hypervector dictionary
def genLevelHVs(totalLevel, D):
    print('Generating level HVs')
    levelHVs = dict()
    indexVector = range(D)
    nextLevel = int((D/2/totalLevel))
    change = int(D / 2)
    for level in range(totalLevel):
        name = level
        if(level == 0):
            base = np.full(D, baseVal)
            toOne = np.random.permutation(indexVector)[:change]
        else:
            toOne = np.random.permutation(indexVector)[:nextLevel]
        for index in toOne:
            base[index] = base[index] * -1
        levelHVs[name] = copy.deepcopy(base)
    return levelHVs   

def EncodeToHV_wrapper(inputBuffer, position, D=10000, levelHVs={}, levelList=[]):
    return position, EncodeToHV(inputBuffer, D, levelHVs, levelList)

#Encodes a single datapoint into a hypervector
#Inputs:
#   inputBuffer: data to encode
#   D: dimensionality
#   levelHVs: level hypervector dictionary
#   IDHVs: ID hypervector dictionary
#Outputs:
#   sumHV: encoded data
def EncodeToHV(inputBuffer, D, levelHVs, levelList):
    sumHV = np.zeros(D, dtype = np.int)
    for keyVal in range(len(inputBuffer)):
        key = numToKey(inputBuffer[keyVal], levelList)
        levelHV = levelHVs[key] 
        sumHV = sumHV + np.roll(levelHV, keyVal)
    return sumHV
                    
# This function attempts to guess the class of the input vector based on the model given
#Inputs:
#   classHVs: class hypervectors
#   inputHV: query hypervector
#Outputs:
#   guess: class that the model classifies the query hypervector as
def checkVector(classHVs, inputHV):
    guess = list(classHVs.keys())[0]
    maximum = np.NINF
    count = {}
    for key in classHVs.keys():
        count[key] = inner_product(classHVs[key], inputHV)
        if (count[key] > maximum):
            guess = key
            maximum = count[key]
    return guess

#Iterates through the training set once to retrain the model
#Inputs:
#   classHVs: class hypervectors
#   testHVs: encoded train data
#   testLabels: training labels
#Outputs:
#   retClassHVs: retrained class hypervectors
#   error: retraining error rate
def trainOneTime(classHVs, trainHVs, trainLabels):
    retClassHVs = copy.deepcopy(classHVs)
    wrong_num = 0
    for index in range(len(trainLabels)):
        guess = checkVector(retClassHVs, trainHVs[index])
        if not (trainLabels[index] == guess):
            wrong_num += 1
            retClassHVs[guess] = retClassHVs[guess] - trainHVs[index]
            retClassHVs[trainLabels[index]] = retClassHVs[trainLabels[index]] + trainHVs[index]
    error = (wrong_num+0.0) / len(trainLabels)
    print('Error: {}'.format(error))
    return retClassHVs, error

#Tests the HD model on the testing set
#Inputs:
#   classHVs: class hypervectors
#   testHVs: encoded test data
#   testLabels: testing labels
#Outputs:
#   accuracy: test accuracy
def test (classHVs, testHVs, testLabels):
    correct = 0
    for index in range(len(testHVs)):
        guess = checkVector(classHVs, testHVs[index])
        if (testLabels[index] == guess):
            correct += 1
    accuracy = (correct / len(testLabels)) * 100
    print('the accuracy is: {}'.format(accuracy))
    return (accuracy)

#Retrains the HD model n times and evaluates the accuracy of the model
#after each retraining iteration
#Inputs:
#   classHVs: class hypervectors
#   trainHVs: encoded training data
#   trainLabels: training labels
#   testHVs: encoded test data
#   testLabels: testing labels
#Outputs:
#   accuracy: array containing the accuracies after each retraining iteration
def trainNTimes (classHVs, trainHVs, trainLabels, testHVs, testLabels, n):
    accuracy = []
    currClassHV = copy.deepcopy(classHVs)
    accuracy.append(test(currClassHV, testHVs, testLabels))
    prev_error = np.Inf
    for i in range(n):
        print('iteration: {}'.format(i))
        currClassHV, error = trainOneTime(currClassHV, trainHVs, trainLabels)
        accuracy.append(test(currClassHV, testHVs, testLabels))
        if error == prev_error:
            break
        prev_error = error
    return accuracy

#Creates an HD model object, encodes the training and testing data, and
#performs the initial training of the HD model
#Inputs:
#   trainData: training set
#   trainLabes: training labels
#   testData: testing set
#   testLabels: testing labels
#   D: dimensionality
#   nLevels: number of level hypervectors
#   datasetName: name of the dataset
#   workdir: working directory
#   spark: use Spark
#   gpu: use GPU
#   nproc: number of parallel jobs
#Outputs:
#   model: HDModel object containing the encoded data, labels, and class HVs
def buildHDModel(trainData, trainLabels, testData, testLables, D, nLevels, datasetName, workdir='./', spark=False, gpu=False, nproc=1):
    # Initialise HDModel
    model = HDModel( datasetName, trainData, trainLabels, testData, testLables, 
                     D, nLevels, workdir, spark=spark, gpu=gpu, nproc=nproc )
    # Build training HD vectors
    model.buildBufferHVs("train")
    # Test model
    model.buildBufferHVs("test")
    return model

# Last line which starts with '#' will be considered header
# Last column contains classes
# First column contains the IDs of the observations
# Header line contains the feature names
def buildDataset( filepath, separator=',', training=80, seed=0 ):
    # Set a seed for the random sampling of the dataset
    random.seed( seed )
    # Retrieve classes
    classes = [ ]
    content = [ ]
    labels = [ ]
    with open( filepath ) as file:
        for line in file:
            line = line.strip()
            if line:
                if not line.startswith( '#' ):
                    line_split = line.split( separator )
                    classes.append( line_split[ 0 ] )
                    content.append( [ float( value ) for value in line_split[ 1: -1 ] ] )
                    labels.append( line_split[ -1 ] )
    trainData = [ ]
    trainLabels = [ ]
    testData = [ ]
    testLabels = [ ]
    for classid in list( set( classes ) ):
        training_amount = int( ( float( classes.count( classid ) ) * float( training ) ) / 100.0 )
        # Create the training set by random sampling
        indices = [ pos for pos in classes if classes[ pos ] == classid ]
        training_indices = random.sample( indices, training_amount )
        trainData.extend( [ content[ idx ] for idx in training_indices ] )
        trainLabels.extends( [ classid ]*len( training_indices ) )
        testData.extend( [ content[ idx ] for idx in indices if idx not in training_indices ] )
        testLabels.extends( [ classid ]*( len( indices )-len( training_indices ) ) )
    return trainData, trainLabels, testData, testLabels
