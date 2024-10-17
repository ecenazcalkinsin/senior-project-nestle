#| include: false
library(magrittr)
library(tidyverse)
library(data.table)
library(readxl)
library(tsibble)
library(feasts)
library(fable)
library(fabletools)
library(DBI)
library(RSQLite)
library(readxl)
library(dbplyr)

db_path <- "{db_path}"
con <- dbConnect(RSQLite::SQLite(), db_path)
machine <-'{machine_name}'
query <- sprintf("SELECT *, CAST(article AS TEXT) AS article FROM all_transaction_log WHERE machine = '%s'", machine)
d1 <- dbGetQuery(con, query)
dbDisconnect(con)

con <- dbConnect(RSQLite::SQLite(), db_path)
query <- "SELECT * FROM recipe"
recipe <- dbGetQuery(con, query)
dbDisconnect(con)

recipe_df_long <- recipe %>%        # convert to long format (one column for the ingredient names)
  pivot_longer(cols = -`ProductName`, names_to = "ingredient", values_to = "amount")

last_day <- as.POSIXct("2023-12-1") # cut-off date
sales_df <- d1 %>% bind_rows() %>% 
  filter(date <= last_day) 
# mutate(across(where(is.character), factor)) 
sales_df$product_name <- gsub("CaffÃ¨", "Coffee", sales_df$product_name)
sales_df %>% tail()

sales_df$date <- as.POSIXct(sales_df$date, tz = "UTC")
sales_df_hourly <- sales_df %>% 
  mutate(date_hour = floor_date(date, "hour")) %>% # Truncate to hour
  group_by(date_hour, machine, product_name) %>%
  summarise(TotalCoffeeSales = sum(quantity), .groups = "drop")

ingredients_ts <- sales_df_hourly %>% 
  left_join(recipe_df_long, by = c("product_name" = "ProductName")) %>% 
  filter(!is.na(ingredient)) %>%
  group_by(date_hour, machine, ingredient) %>% 
  summarize(amount = sum(TotalCoffeeSales*amount), .groups = "drop") %>% 
  as_tsibble(key = c(machine, ingredient), index = date_hour) %>% 
  fill_gaps() %>% 
  replace_na(list(amount = 0))

dcmp_dwm <- decomposition_model(
  STL(sqrt(amount) ~ season(period = 24) +
        season(period = 7*24) +
        season(period= 7*24*4),
      robust = TRUE),
  ETS(season_adjust ~ season("N"))
)

dcmp_dm <- decomposition_model(
  STL(sqrt(amount) ~ season(period = 24) +
        season(period= 7*24*4),
      robust = TRUE),
  ETS(season_adjust ~ season("N"))
)

dcmp_d <- decomposition_model(
  STL(sqrt(amount) ~ season(period = 24),
      robust = TRUE),
  ETS(season_adjust ~ season("N"))
)

ingredients_ts_train <- ingredients_ts %>% 
  filter_index(. ~ "2023-10-31")

ingredients_ts_test <- ingredients_ts %>% 
  filter_index("2023-11-1" ~ .)

ingredients_mable_train <- ingredients_ts_train %>% 
  model(dcmp_dwm = dcmp_dwm,
        dcmp_dm = dcmp_dm,
        dcmp_d = dcmp_d
  )

ingredients_fable_test <- ingredients_mable_train %>% 
  forecast(h = "2 days", simulate = TRUE)

a <- bind_rows(
  accuracy(ingredients_mable_train),
  accuracy(ingredients_fable_test, ingredients_ts)
) %>% 
  arrange(desc(.type), .model)


best_models <- a %>%
  filter(!is.na(MASE)) %>%
  group_by(ingredient) %>%
  filter(MASE == min(MASE, na.rm = TRUE)) %>%
  select(ingredient, .model)


forecast_result <- ingredients_fable_test %>%
  semi_join(best_models, by = c("ingredient", ".model"))


forecast_df <- as.data.frame(forecast_result) %>%
  select(date_hour, machine, ingredient, .mean) %>%
  mutate(.mean = round(.mean, 0))

names(forecast_df)[names(forecast_df) == ".mean"] <- "amount"

forecast_df$date_hour <- strftime(forecast_df$date_hour, format = "%Y-%m-%d %H:%M:%S")
db_path <- "{db_path}"
con <- dbConnect(RSQLite::SQLite(), db_path)
dbWriteTable(con, "FORECAST", forecast_df, rowNames = FALSE, append = TRUE)
dbDisconnect(con)


```
