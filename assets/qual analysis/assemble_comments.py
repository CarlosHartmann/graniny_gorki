'''
assemble_comments.py: Script to assemble and analyze comments from human and LLM responses.
'''

import os

def assemble_human_comments():
    sheet_paths = [
        '/Users/Carlitos/Documents/GitHub/graniny_gorki/raw_data/Humans/linguists_prolific/sheet_version/Block A/block_A_11_5f6ce7a067864711ebb0f66e.csv',
        '/Users/Carlitos/Documents/GitHub/graniny_gorki/raw_data/Humans/linguists_prolific/sheet_version/Block B/Block_B_13_655788501826eeea1b788f8b.csv']
    pilotpath = '/Users/Carlitos/Documents/GitHub/graniny_gorki/raw_data/Humans/pilot'
    sheet_paths.append([elem for elem in os.listdir(pilotpath) if elem.endswith('.csv')][0])

