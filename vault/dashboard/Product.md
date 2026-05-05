TABLE area, severity, derived_from, status
FROM "11_Product_Insights"
WHERE type = "product_insight"
SORT file.ctime DESC