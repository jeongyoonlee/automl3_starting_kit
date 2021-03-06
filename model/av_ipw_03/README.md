# `av_ipw`: An adversarial validation with inverse propensity weighting

This model is based on the `baseline` model, which uses the setup as follows:

* At each batch, it trains a model only with new training data without using previous training data
* At each batch, it uses 100% of training data
* It uses LightGBM's LGBMClassifier
* It label-encodes categorical features with missing values as a new label

We added an adversarial validation to `baseline` as follows:

* At each batch, it trains an adversarial validation model with the training and test feature data
* At each batch, it uses the p / (1 - p), where p is the prediction of the adversarial validation model, as a sample weight
