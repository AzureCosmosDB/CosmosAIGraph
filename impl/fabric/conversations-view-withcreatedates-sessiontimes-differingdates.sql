CREATE VIEW [cosmosdemosdp].[conversationsview] AS
WITH PromptData AS (
    SELECT 
        c.conversation_id,
        -- Convert created_date to datetime, rounding to seconds
        CONVERT(DATETIME, LEFT(c.created_date, 19), 120) AS created_date_hour,  -- Including the seconds
        CONVERT(DATE, c.created_date) AS created_date_day,
        -- Convert created_date directly to DATETIME at the second grain
        CONVERT(DATETIME, LEFT(c.created_date, 19), 120) AS created_date,
        c.userpk,
        p.Prompt,
        ROW_NUMBER() OVER (PARTITION BY c.conversation_id ORDER BY (SELECT NULL)) AS PromptIndex
    FROM
        cosmosdemosdp.conversations c
    CROSS APPLY OPENJSON(c.prompts) 
        WITH (
            Prompt NVARCHAR(MAX) '$'
        ) AS p
),
CompletionData AS (
    SELECT 
        c.conversation_id,
        j.completion_id,
        j.completion_tokens,
        j.prompt_tokens,
        j.total_tokens,
        j.Completion,
        j.Model,
        j.rag_strategy,
        -- Convert j.created_date to DATETIME at the second grain
        CONVERT(DATETIME, LEFT(j.created_date, 19), 120) AS completion_created_date,
        -- Convert j.created_date to DATETIME but truncated at the hour (removes minutes and seconds)
        CONVERT(DATETIME, LEFT(j.created_date, 13) + ':00:00', 120) AS completion_created_date_hour,
        ROW_NUMBER() OVER (PARTITION BY c.conversation_id ORDER BY (SELECT NULL)) AS CompletionIndex
    FROM
        cosmosdemosdp.conversations c
    CROSS APPLY OPENJSON(c.completions) 
        WITH (
            completion_id NVARCHAR(MAX) '$.completion_id',
            completion_tokens INT '$.usage.completion_tokens',
            prompt_tokens INT '$.usage.prompt_tokens',
            total_tokens INT '$.usage.total_tokens',
            Completion NVARCHAR(MAX) '$.content',
            Model NVARCHAR(MAX) '$.model',
            rag_strategy NVARCHAR(MAX) '$.rag_strategy',  
            created_date NVARCHAR(50) '$.created_date'   
        ) AS j
)
SELECT 
    p.conversation_id,
    p.created_date_hour,
    p.created_date_day,
    p.created_date,
    p.userpk,
    p.Prompt,
    c.completion_id,
    c.completion_tokens,
    c.prompt_tokens,
    c.total_tokens,
    c.Completion,
    c.Model,
    c.rag_strategy,
    c.completion_created_date,
    c.completion_created_date_hour  -- Add the new column for truncated created_date (hour level)
FROM
    PromptData p
JOIN
    CompletionData c
    ON p.conversation_id = c.conversation_id 
    AND p.PromptIndex = c.CompletionIndex;
