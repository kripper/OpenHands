reset
YOUR_OUTPUT_JSONL=evaluation/evaluation_outputs/outputs/swe-bench-lite/CodeActAgent/gemini-1.5-pro-exp-0827_maxiter_18_N_v1.9-no-hint/output.jsonl
INSTANCE_ID=django__django-11179
DATASET_NAME=princeton-nlp/SWE-bench_Verified
SPLIT=test

./evaluation/swe_bench/scripts/eval_infer.sh $YOUR_OUTPUT_JSONL $INSTANCE_ID $DATASET_NAME $SPLIT

# espeak 'e'
