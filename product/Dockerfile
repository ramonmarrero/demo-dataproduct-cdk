FROM rocker/r-ver:4.0.0

RUN R -e "install.packages(c('ggplot2'), \
           dependencies=TRUE, repos='http://cran.rstudio.com/')"

# Create app directory
RUN mkdir /home/dataproduct
WORKDIR /home/dataproduct

# Copy files
COPY . /home/dataproduct/


