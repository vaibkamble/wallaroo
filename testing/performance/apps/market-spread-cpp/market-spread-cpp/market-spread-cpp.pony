/*

Copyright 2017 The Wallaroo Authors.

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 implied. See the License for the specific language governing
 permissions and limitations under the License.

*/

"""
Setting up a market-spread-cpp run (in order):
1) reports sink:
nc -l 127.0.0.1 5555 >> /dev/null

2) metrics sink:
nc -l 127.0.0.1 5001 >> /dev/null

3a) single worker
./market-spread-cpp -i 127.0.0.1:7000,127.0.0.1:7001 -o 127.0.0.1:5555 -m 127.0.0.1:501 -c 127.0.0.1:6000 -d 127.0.0.1:6001 -n worker-name -t --ponythreads=4 --ponynoblock

3b) multi-worker
./market-spread-cpp -i 127.0.0.1:7000,127.0.0.1:7001 -o 127.0.0.1:5555 -m 127.0.0.1:5001 -c 127.0.0.1:6000 -d 127.0.0.1:6001 -n node-name --ponythreads=4 --ponynoblock -t -w 2

./market-spread-cpp -i 127.0.0.1:7000,127.0.0.1:7001 -o 127.0.0.1:5555 -m 127.0.0.1:5001 -c 127.0.0.1:6000 -n worker2 --ponythreads=4 --ponynoblock

4) initialization:
giles/sender/sender -h 127.0.0.1:7000 -m 5000000 -s 300 -i 5_000_000 -f testing/data/market_spread/initial-nbbo-fixish.msg -r --ponythreads=1 -y -g 57 -w

5) orders:
giles/sender/sender -h 127.0.0.1:7000 -m 5000000 -s 300 -i 5_000_000 -f testing/data/market_spread/orders/r3k-symbols_orders-fixish.msg -r --ponythreads=1 -y -g 57 -w

6) nbbo:
giles/sender/sender -h 127.0.0.1:7001 -m 10000000 -s 300 -i 2_500_000 -f testing/data/market_spread/nbbo/r3k-symbols_nbbo-fixish.msg -r --ponythreads=1 -y -g 46 -w
"""

use "wallaroo/cpp_api/pony"

use "lib:wallaroo"
use "lib:c++" if osx
use "lib:stdc++" if linux

use "lib:market-spread-cpp"

actor Main
  new create(env: Env) =>
    WallarooMain(env)
