import instagramcrawler
import os

IDs = open('path/user_list.txt')
results = IDs.read().splitlines()

for i in range(len(results)):
    os.system("python instagramcrawler.py -q '" + results[i] + "' -t 'profile_img' -n 200 -a auth.json")