# Measured software example — SYNTHETIC PRACTICE DATA

This report is generated from the bundled simulation. It is not evidence of real retail accuracy or inventory savings.

Selected method: **random_forest**, selected exclusively by validation MAE.

| Model | Validation MAE | Test MAE | Test RMSE | Test bias |
|---|---:|---:|---:|---:|
| naive | 9.4286 | 10.3125 | 12.7951 | 3.9732 |
| seasonal_naive | 6.5893 | 6.4554 | 8.0534 | -0.4464 |
| linear_regression | 5.2863 | 5.2157 | 6.5549 | -0.6541 |
| random_forest | 5.2322 | 5.3423 | 6.7174 | -0.8688 |

The test observations were not used to select the method. The serving refit uses all known history only after evaluation; these held-out metrics belong to evaluation fits.

For your internship results, repeat on licensed real historical sales and document source, exclusions, assumptions and independent evaluation. No observed inventory is bundled.

See manifest.json for data/model hashes, split dates, forecast origins and package versions. No trained binary model is distributed; run the training command to create your own artifact.
