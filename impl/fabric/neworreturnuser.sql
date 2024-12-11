CREATE VIEW cosmosdemosdp.neworreturn AS
WITH UserRank AS (
    SELECT 
        created_date_day,
        userpk,
        total_tokens,
        ROW_NUMBER() OVER (PARTITION BY userpk ORDER BY created_date_day) AS user_appearance_rank
    FROM [cosmosdemosdp].[conversationsview]  -- Use the correct schema prefix
)
SELECT 
    created_date_day,
    userpk,
    total_tokens,
    CASE 
        WHEN user_appearance_rank = 1 THEN 'New'  -- First appearance (New user)
        ELSE 'Returning'                          -- All subsequent appearances (Returning user)
    END AS user_status
FROM UserRank;
