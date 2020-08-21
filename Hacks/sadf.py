from multiproc import *

# Try it out. Change the directory name as desired. 

if __name__ == '__main__':

    digest_map = build_digest_map("./")
    print(len(digest_map))
    print('\n\n\n\n')
    print(digest_map)