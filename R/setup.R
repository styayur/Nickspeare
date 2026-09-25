# Run in RStudio or with Rscript R/setup.R. Install only missing dependencies.
required <- c("xml2", "jsonlite")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) install.packages(missing, repos = "https://cloud.r-project.org")
print(vapply(required, function(x) as.character(packageVersion(x)), character(1)))
