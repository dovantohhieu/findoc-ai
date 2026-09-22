# So sánh retrieval — eval/gold30.yaml, k=5

| chỉ số | dense | bm25 | hybrid_rrf |
|---|---|---|---|
| Recall@5 | 0.633 | 0.633 | 0.600 |
| Hit@5 | 0.633 | 0.633 | 0.600 |
| Hit@1 | 0.500 | 0.500 | 0.500 |
| MRR | 0.541 | 0.547 | 0.544 |
| p50 ms | 81 | 33 | 108 |

## Recall@5 theo loại câu hỏi

| kind | n | dense | bm25 | hybrid_rrf |
|---|---|---|---|---|
| date_range | 2 | 0.000 | 0.500 | 0.500 |
| exact_lookup | 5 | 1.000 | 1.000 | 1.000 |
| item_lookup | 3 | 0.667 | 0.000 | 0.000 |
| metadata_filter | 4 | 0.500 | 0.500 | 0.500 |
| negative | 1 | 0.000 | 0.000 | 0.000 |
| numeric | 4 | 1.000 | 1.000 | 1.000 |
| paraphrase | 5 | 0.800 | 0.800 | 0.800 |
| semantic | 4 | 0.250 | 0.500 | 0.250 |
| synonym | 2 | 0.500 | 0.500 | 0.500 |