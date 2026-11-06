# Boston housing data, corrected version

`boston_corrected.csv` has 506 rows and 21 columns. It is the Harrison and Rubinfeld (1978)
data with the corrections of Gilley and Pace (1996) and the tract coordinates added by
Pace and Gilley (1997), converted from the tab-separated StatLib file
<http://lib.stat.cmu.edu/datasets/boston_corrected.txt> to comma-separated values.
The only edit is the first header name, `OBS.` -> `OBS`.

| Column | Meaning |
| --- | --- |
| OBS | observation number |
| TOWN | town name |
| TOWN# | town code |
| TRACT | census tract |
| LON, LAT | tract longitude and latitude |
| MEDV | median value of owner-occupied homes in $1000 (original, censored at 50) |
| CMEDV | corrected MEDV |
| CRIM ... LSTAT | the 13 predictors of the original data (see `../boston/boston_description.txt`) |

## Use in the RCGP experiments

The UCI experiments in RCGP use the original `housing.data` (target MEDV). The corrected
file is kept for comparison: `CMEDV` fixes eight miscoded values, and `MEDV = 50.0`
marks 16 censored rows, which behave like outliers for a Gaussian likelihood.

## References

- Harrison, D., Rubinfeld, D. L. (1978). Hedonic housing prices and the demand for clean air. *J. Environ. Econ. Manage.* 5, 81–102.
- Gilley, O. W., Pace, R. K. (1996). On the Harrison and Rubinfeld data. *J. Environ. Econ. Manage.* 31, 403–405.
- Pace, R. K., Gilley, O. W. (1997). Using the spatial configuration of the data to improve estimation. *J. Real Estate Finance Econ.* 14, 333–340.
- The same corrected data are distributed as `boston.c` in the R package spData (CC0).
