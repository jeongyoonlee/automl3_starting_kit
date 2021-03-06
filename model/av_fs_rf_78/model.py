'''
Sample predictive model.
You must supply at least 4 methods:
- fit: trains the model.
- predict: uses the model to perform predictions.
- save: saves the model.
- load: reloads the model.
PLEASE NOTE THAT WE ARE PASSING THE INFO OF THE DATA SET AS AN ADDITIONAL ARGUMENT!
'''
import pickle
import data_converter
import logging
import numpy as np   # We recommend to use numpy arrays
from os.path import isfile, dirname, abspath
import time
from lightgbm import LGBMClassifier
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.tree import DecisionTreeClassifier
from kaggler.preprocessing import LabelEncoder


SEED = 42
GINI_THRESHOLD = .1

model_name = dirname(abspath(__file__))
SEED = int(model_name[-2:])

logging.basicConfig(format='%(asctime)s   %(levelname)s   %(message)s',
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=f'{model_name}.log')


params = {'num_leaves': 31,
          'max_depth': 5,
          'learning_rate': .1,
          'n_estimators': 100,
          'subsample': .5,
          'subsample_freq': 1,
          'colsample_bytree': .8,
          'reg_alpha': 1,
          'reg_lambda': 1,
          'importance_type': 'gain',
          'n_jobs': -1,
          'random_state': SEED,
          'metric': 'auc'}


class Model:
    def __init__(self,datainfo,timeinfo):
        '''
        This constructor is supposed to initialize data members.
        Use triple quotes for function documentation.
        '''
        # Just logging.info some info from the datainfo variable
        logging.info("The Budget for this data set is: %d seconds" %datainfo['time_budget'])

        logging.info("Loaded %d time features, %d numerical Features, %d categorical features and %d multi valued categorical variables" %(datainfo['loaded_feat_types'][0], datainfo['loaded_feat_types'][1],datainfo['loaded_feat_types'][2],datainfo['loaded_feat_types'][3]))
        overall_spenttime=time.time()-timeinfo[0]
        dataset_spenttime=time.time()-timeinfo[1]
        logging.info("[***] Overall time spent %5.2f sec" % overall_spenttime)
        logging.info("[***] Dataset time spent %5.2f sec" % dataset_spenttime)
        self.num_train_samples=0
        self.num_feat=1
        self.num_labels=1
        self.is_trained=False
        self.clf = LGBMClassifier(**params)
        # Here you may have parameters and hyper-parameters

    def fit(self, F, y, datainfo,timeinfo):
        '''
        This function should train the model parameters.
        Here we do nothing in this example...
        Args:
            X: Training data matrix of dim num_train_samples * num_feat.
            y: Training label matrix of dim num_train_samples * num_labels.
        Both inputs are numpy arrays.
        If fit is called multiple times on incremental data (train, test1, test2, etc.)
        you should warm-start your training from the pre-trained model. Past data will
        NOT be available for re-training.
        '''

        overall_spenttime=time.time()-timeinfo[0]
        dataset_spenttime=time.time()-timeinfo[1]

        logging.info("[***] Overall time spent %5.2f sec" % overall_spenttime)
        logging.info("[***] Dataset time spent %5.2f sec" % dataset_spenttime)

        date_cols = datainfo['loaded_feat_types'][0]
        numeric_cols = datainfo['loaded_feat_types'][1]
        categorical_cols = datainfo['loaded_feat_types'][2]
        multicategorical_cols = datainfo['loaded_feat_types'][3]

        # Get numerical variables and replace NaNs with 0s
        self.X = np.nan_to_num(F['numerical'])
        self.y = y

        # Frequency encode categorical variables and concatenate them with numerical variables
        if categorical_cols > 0:
            self.cat_encs = LabelEncoder()
            X_cat = self.cat_encs.fit_transform(F['CAT']).values
            self.X = np.concatenate((self.X, X_cat), axis=1)
            del X_cat

        self.num_train_samples = self.X.shape[0]
        self.num_feat = self.X.shape[1]
        num_train_samples = y.shape[0]

        logging.info ("The whole available data is: ")
        logging.info(("Real-FIT: dim(X)= [{:d}, {:d}]").format(self.X.shape[0],self.X.shape[1]))
        logging.info(("Real-FIT: dim(y)= [{:d}, {:d}]").format(self.y.shape[0], self.num_labels))

        self.is_trained=True

    def predict(self, F,datainfo,timeinfo):
        '''
        This function should provide predictions of labels on (test) data.
        Here we just return random values...
        Make sure that the predicted values are in the correct format for the scoring
        metric. For example, binary classification problems often expect predictions
        in the form of a discriminant value (if the area under the ROC curve it the metric)
        rather that predictions of the class labels themselves.
        The function predict eventually casdn return probabilities or continuous values.
        '''

        overall_spenttime=time.time()-timeinfo[0]
        dataset_spenttime=time.time()-timeinfo[1]

        logging.info("[***] Overall time spent %5.2f sec" % overall_spenttime)
        logging.info("[***] Dataset time spent %5.2f sec" % dataset_spenttime)

        date_cols = datainfo['loaded_feat_types'][0]
        numeric_cols = datainfo['loaded_feat_types'][1]
        categorical_cols = datainfo['loaded_feat_types'][2]
        multicategorical_cols = datainfo['loaded_feat_types'][3]

        # Get numerical variables and replace NaNs with 0s
        X = np.nan_to_num(F['numerical'])

        # Frequency encode categorical variables and concatenate them with numerical variables
        if categorical_cols > 0:
            X_cat = self.cat_encs.transform(F['CAT']).values
            X = np.concatenate((X, X_cat), axis=1)
            del X_cat

        # Adversarial validation
        logging.info('AV: starting adversarial validation...')

        np.random.seed(SEED)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

        n_trn = self.X.shape[0]
        n_tst = X.shape[0]
        n_feature = X.shape[1]

        X_all = np.vstack((self.X, X))
        y_all = np.concatenate((np.zeros(n_trn,), np.ones(n_tst,)))
        logging.info(f'AV: {X_all.shape}, {y_all.shape}')
        logging.info(f'AV: {np.unique(y_all)}')

        av_auc = 1.
        cols = np.arange(n_feature)
        count = 0
        av_auc_threshold = .8
        while av_auc > av_auc_threshold:
            model_av = RandomForestClassifier(min_samples_leaf=20,
                                              min_impurity_decrease=.01,
                                              random_state=SEED)
            model_av.fit(X_all[:, cols], y_all)

            ps_all = model_av.predict_proba(X_all[:, cols])[:, 1]
            av_auc = roc_auc_score(y_all, ps_all)
            logging.info(f'AV #{count}: AUC={av_auc * 100: 3.2f}')

            imp = pd.DataFrame({'feature': cols,
                                'importance': model_av.feature_importances_})
            imp = imp.sort_values('importance', ascending=False)
            logging.info(f'AV #{count}: feature importance\n{imp.head(10)}')

            # Select features
            cols_to_drop = imp.loc[imp.importance > GINI_THRESHOLD, 'feature'].values[:int(np.ceil(len(cols) * .1))]
            logging.info(f'AV #{count}: columns to drop: {cols_to_drop}')
            if av_auc <= av_auc_threshold or len(cols_to_drop) == 0:
                break

            cols = [x for x in cols if x not in cols_to_drop]
            logging.info(f'AV #{count}: columns to keep: {cols}')
            count += 1

        X = X[:, cols]
        self.X = self.X[:, cols]
        logging.info(f'AV: # of features after selection: {X.shape[1]}')

        # Training
        X_trn, X_val, y_trn, y_val = train_test_split(self.X, self.y, test_size=.25, random_state=SEED)
        self.clf.fit(X_trn, y_trn,
                     eval_set=(X_val, y_val),
                     early_stopping_rounds=10,
                     verbose=10)

        num_test_samples = X.shape[0]
        if X.ndim > 1: num_feat = X.shape[1]
        logging.info(("PREDICT: dim(X)= [{:d}, {:d}]").format(num_test_samples, num_feat))
        logging.info(("PREDICT: dim(y)= [{:d}, {:d}]").format(num_test_samples, self.num_labels))
        y= self.clf.predict_proba(X)[:, 1]
        y= np.transpose(y)
        return y

    def save(self, path="./"):
        pickle.dump(self, open(path + '_model.pickle', "w"))

    def load(self, path="./"):
        modelfile = path + '_model.pickle'
        if isfile(modelfile):
            with open(modelfile) as f:
                self = pickle.load(f)
            logging.info("Model reloaded from: " + modelfile)
        return self
