Все цифры — без spf13-cobra (универсально трудный target, 0-3 успехов у всех)
Каждая клетка: success% / branch% / diff% / тестов / токенов

=== Qwen 7B (floor) ===
  config                     succ% branch%  diff%  тестов   токенов    vs full
  full                        28.6    70.0   62.1       6   571,974                     
  no-coverage                 14.3       —      —       3   549,919          Δsucc=-14pp
  no-pruning                   0.0       —      —       0   541,417          Δsucc=-29pp
  no-smart-diff               28.6    83.8   93.9       6   573,742 Δsucc=+0pp, Δbranch=+14
  no-structured-feedback       9.5   100.0  100.0       2   531,422 Δsucc=-19pp, Δbranch=+30
  no-types                    19.0    58.3   56.6       4   531,908 Δsucc=-10pp, Δbranch=-12

=== Qwen 30B ===
  config                     succ% branch%  diff%  тестов   токенов    vs full
  full                        66.7    82.8   84.2      15   758,241                     
  no-coverage                 57.1       —      —      15   711,813          Δsucc=-10pp
  no-pruning                  14.3       —  100.0       3   718,385          Δsucc=-52pp
  no-smart-diff               76.2    73.2   81.9      18   847,971 Δsucc=+10pp, Δbranch=-10
  no-structured-feedback      66.7    77.7   90.5      15   735,284 Δsucc=+0pp, Δbranch=-5
  no-types                    47.6    75.0   85.4      10   713,322 Δsucc=-19pp, Δbranch=-8

=== Llama 70B ===
  config                     succ% branch%  diff%  тестов   токенов    vs full
  full                        66.7    69.1   71.3      15   590,356                     
  no-coverage                 76.2       —      —      16   499,440          Δsucc=+10pp
  no-pruning                  19.0   100.0  100.0       4   541,831 Δsucc=-48pp, Δbranch=+31
  no-smart-diff               66.7    75.0   72.9      14   607,334 Δsucc=+0pp, Δbranch=+6
  no-structured-feedback      52.4    67.6   71.5      12   550,826 Δsucc=-14pp, Δbranch=-1
  no-types                    61.9    72.4   84.1      13   551,789 Δsucc=-5pp, Δbranch=+3

=== GPT-4o-mini ===
  config                     succ% branch%  diff%  тестов   токенов    vs full
  full                        85.7    72.5   77.6      20   501,697                     
  no-coverage                 71.4       —      —      16   475,261          Δsucc=-14pp
  no-pruning                  28.6   100.0  100.0       6   507,020 Δsucc=-57pp, Δbranch=+27
  no-smart-diff               95.2    71.5   74.3      20   535,740 Δsucc=+10pp, Δbranch=-1
  no-structured-feedback      95.2    77.2   77.8      20   482,315 Δsucc=+10pp, Δbranch=+5
  no-types                    90.5    79.3   75.0      20   556,680 Δsucc=+5pp, Δbranch=+7

=== DeepSeek V3 ===
  config                     succ% branch%  diff%  тестов   токенов    vs full
  full                        66.7    80.0   73.1      16   543,243                     
  no-coverage                 71.4       —      —      16   510,241           Δsucc=+5pp
  no-pruning                  28.6    68.6   80.4       6   572,526 Δsucc=-38pp, Δbranch=-11
  no-smart-diff               81.0    77.6   77.1      20   612,673 Δsucc=+14pp, Δbranch=-2
  no-structured-feedback      81.0    81.2   83.3      19   497,604 Δsucc=+14pp, Δbranch=+1
  no-types                    52.4    71.0   78.9      11   553,212 Δsucc=-14pp, Δbranch=-9

=== Claude 3.5 Haiku ===
  config                     succ% branch%  diff%  тестов   токенов    vs full
  full                        85.7    82.8   89.8      18   710,486                     
  no-coverage                 81.0       —      —      17   677,863           Δsucc=-5pp
  no-pruning                  14.3   100.0  100.0       3   689,276 Δsucc=-71pp, Δbranch=+17
  no-smart-diff               85.7    85.9   79.8      18   768,841 Δsucc=+0pp, Δbranch=+3
  no-structured-feedback      81.0    89.4   79.2      17   659,195 Δsucc=-5pp, Δbranch=+7
  no-types                    66.7    81.7   87.7      15   704,662 Δsucc=-19pp, Δbranch=-1

=== Gemini 3 Flash ===
  config                     succ% branch%  diff%  тестов   токенов    vs full
  full                       100.0    83.8   89.4      24   715,996                     
  no-coverage                 95.2       —      —      24   624,689           Δsucc=-5pp
  no-pruning                  57.1    80.4   92.1      12   690,365 Δsucc=-43pp, Δbranch=-3
  no-smart-diff              100.0    83.6   82.5      23   730,414 Δsucc=+0pp, Δbranch=-0
  no-structured-feedback     100.0    85.3   84.9      25   549,559 Δsucc=+0pp, Δbranch=+2
  no-types                    95.2    83.2   91.4      21   726,262 Δsucc=-5pp, Δbranch=-1

