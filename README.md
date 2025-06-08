# ai-roundtable

``` shell
❯ python -m ai_roundtable.cli -h
usage: cli.py [-h] [-a AGENDA] [-m MODEL] [-u BASE_URL] [-c CONFIG] [-t THREAD] [-o OUT] [--disable_stream] [-n MAX_TURNS] [--eval_messages EVAL_MESSAGES] [-e EVAL_OUT] [-s SKIP_EVAL]
              [--user_input_end USER_INPUT_END] [--debug] [--quiet] [--skeleton {minimal,dual,full}] [--instructions INSTRUCTIONS] [-l LANGUAGE]

Discuss with multiple AIs

options:
  -h, --help            show this help message and exit
  -a, --agenda AGENDA   first message to give to AI, agenda. @file_name to specify a file. @- to read from stdin. if not specified and thread file exists, the first statement should be agenda
  -m, --model MODEL     AI model, default: gpt-4o-mini
  -u, --base_url BASE_URL
                        base url of API
  -c, --config CONFIG   config file, default: config.yml
  -t, --thread THREAD   thread file, - means stdin
  -o, --out OUT         thread output, default: null
  --disable_stream      disable message streaming to stdout
  -n, --max_turns MAX_TURNS
                        maximum number of statements, default: 16
  --eval_messages EVAL_MESSAGES
                        maximum number of statements to go back for evaluation, default: 5
  -e, --eval_out EVAL_OUT
                        evaluation output, default: null
  -s, --skip_eval SKIP_EVAL
                        turns skip evaluation, negative value means never evaluate, default: 0
  --user_input_end USER_INPUT_END
                        signal end of user input, default: END
  --debug               enable debug log
  --quiet               quiet log
  --skeleton {minimal,dual,full}
                        display config skeleton
  --instructions INSTRUCTIONS
                        display instructions for n-th speaker (0 means the first speaker), needs config
  -l, --language LANGUAGE
                        preferred language

Examples:
# start discussion
python -m ai_roundtable.cli --skeleton dual > dual.yml
python -m ai_roundtable.cli -c dual.yml -a "Can AI be a friend to humans?"
# continue discussion
python -m ai_roundtable.cli -c dual.yml -a "Can AI be a friend to humans?" -o thread.yml
python -m ai_roundtable.cli -c dual.yml -t thread.yml
# custom model provider
python -m ai_roundtable.cli -c dual.yml -a "Can AI be a friend to humans?" \
  -u "http://localhost:11434/v1" -m "gemma3"

Environment variables:
  OPENAI_API_KEY
    required, API key from OpenAI project
```
