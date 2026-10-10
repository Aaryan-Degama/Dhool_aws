"""What the API and the analysis handlers share."""


def query_all(table, **query):
    """Every item a query matches, page after page: one answer from DynamoDB stops at 1 MB (or at Limit)."""
    while True:
        page = table.query(**query)
        yield from page["Items"]
        if "LastEvaluatedKey" not in page:
            return
        query["ExclusiveStartKey"] = page["LastEvaluatedKey"]
