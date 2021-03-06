import dateutil.parser
import pickle
import os
import time

runtime = time.time()
reddit = "reddit-removed-high-high"     # the name of the dataset you want to create, make sure the folder exists
lastfm = "lastfm-removed-high-high"

dataset = reddit

create_lastfm_cet = False

create_time_filtered_dataset = False
time_filter_months = 2 # number of months of data to include per user, unused if create_time_filtered_dataset is False

create_user_statistic_filtered_dataset = True
if dataset == lastfm:
    avg_session_length = 8.092  # calculated from avg_session_length() in data_profiler.py (lastfm)
    avg_session_count = 645.623  # calculated from avg_session_count() in data_profiler.py (lastfm)
elif dataset == reddit:
    avg_session_length = 3.017  # calculated from avg_session_length() in data_profiler.py (reddit)
    avg_session_count = 62.147  # calculated from avg_session_count() in data_profiler.py (reddit)
remove_above_avg_session_length = True
remove_above_avg_session_count = True

home = os.path.expanduser('~')

# Here you can change the path to the dataset
DATASET_DIR = home + '/datasets/'+dataset

if dataset == lastfm:
    DATASET_FILE = home + '/datasets/' + 'userid-timestamp-artid-artname-traid-traname.tsv'
    USER_INFO_FILE = home + '/datasets/' + 'userid-profile.tsv'
elif dataset == reddit:
    DATASET_FILE = home + '/datasets/' + 'reddit_data.csv'
#DATASET_W_CONVERTED_TIMESTAMPS = DATASET_DIR + '/1_converted_timestamps.pickle'
DATASET_W_CONVERTED_TIMESTAMPS = home + '/datasets' + '/1_converted_timestamps.pickle'
FILTERED_DATASET_W_CONVERTED_TIMESTAMPS = DATASET_DIR + '/filtered_timestamps.pickle'
DATASET_USER_ARTIST_MAPPED = DATASET_DIR + '/2_user_artist_mapped.pickle'
DATASET_USER_SESSIONS = DATASET_DIR + '/3_user_sessions.pickle'
DATASET_TRAIN_TEST_SPLIT = DATASET_DIR + '/4_train_test_split.pickle'
DATASET_BPR_MF = DATASET_DIR + '/bpr-mf_train_test_split.pickle'

if dataset == reddit:
    SESSION_TIMEDELTA = 60*60 # 1 hour
elif dataset == lastfm:
    SESSION_TIMEDELTA = 60*30 # 30 minutes

MAX_SESSION_LENGTH = 20     # maximum number of actions in a session (or more precisely, how far into the future an action affects future actions. This is important for training, but when running, we can have as long sequences as we want! Just need to keep the hidden state and compute the next action)
MAX_SESSION_LENGTH_PRE_SPLIT = MAX_SESSION_LENGTH * 2
MINIMUM_REQUIRED_SESSIONS = 3 # The dual-RNN should have minimum 2 to train + 1 to test
PAD_VALUE = 0


def file_exists(filename):
    return os.path.isfile(filename)

def load_pickle(pickle_file):
    return pickle.load(open(pickle_file, 'rb'))

def save_pickle(data_object, data_file):
    pickle.dump(data_object, open(data_file, 'wb'))

def convert_timestamps_reddit():
    dataset_list = []
    with open(DATASET_FILE, 'rt', buffering=10000, encoding='utf8') as dataset:
        for line in dataset:
            line = line.rstrip()
            line = line.split(',')
            if line[2] == 'utc':
                continue
            user_id     = line[0]
            subreddit   = line[1]
            timestamp   = float(line[2])
            dataset_list.append( [user_id, timestamp, subreddit] )
    
    dataset_list = list(reversed(dataset_list))

    save_pickle(dataset_list, DATASET_W_CONVERTED_TIMESTAMPS)

cet = [
"norway",
"sweden",
"denmark",
"germany",
"france",
"netherlands",
"belgium",
"spain",
"italy",
"switzerland",
"austria",
"poland",
"czech republic",
"slovenia",
"slovakia",
"croatia",
"hungary",
"bosnia hercegovina"
]

def convert_timestamps_lastfm():
    last_user_id = ""
    skip_country = False
    dataset_list = []
    num_skipped = 0
    count = 0
    t_skip = 0
    t_non_skip = 0
    user_info = open(USER_INFO_FILE, 'r', buffering=10000, encoding='utf8')
    with open(DATASET_FILE, 'rt', buffering=10000, encoding='utf8') as dataset:
        for line in dataset:
            line = line.split('\t')
            user_id     = line[0]
            timestamp   = (dateutil.parser.parse(line[1])).timestamp()
            artist_id   = line[2]
            artist_name = line[3]
            if user_id != last_user_id:
                last_user_id = user_id
                print(user_id)
            if create_lastfm_cet and (user_id != last_user_id or last_user_id == ""):
                count += 1
                profile = user_info.readline()
                profile = profile.split('\t')
                country = profile[3]
                print(country, str(count))
                last_user_id = user_id
                if country.lower() not in cet:
                    print("no match")
                    skip_country = True
                    num_skipped += 1
                else:
                    print("match")
                    skip_country = False
            if skip_country:
                continue

            dataset_list.append( [user_id, timestamp, artist_id, artist_name] )

    dataset_list = list(reversed(dataset_list))

    save_pickle(dataset_list, DATASET_W_CONVERTED_TIMESTAMPS)

def filter_timestamps():
    ##########################
    # filter out events to only include those in a given interval
    ##########################
    
    new_dataset_list = []
    last_user_id = ""
    first_user_timestamp = ""
    t_skip = 0
    t_non_skip = 0

    dataset_list = load_pickle(DATASET_W_CONVERTED_TIMESTAMPS)

    for line in dataset_list:
        user_id     = line[0]
        timestamp   = line[1]
        if last_user_id != user_id:
            first_user_timestamp = timestamp
            last_user_id = user_id
        if create_time_filtered_dataset:
            if time_filter_months == 1 and timestamp - first_user_timestamp > 25e5:  # about one month
                t_skip += 1
                continue
            elif time_filter_months == 2 and timestamp - first_user_timestamp > 5e6:  # about two months
                t_skip += 1
                continue
            elif time_filter_months == 3 and timestamp - first_user_timestamp > 8e6: # about three months
                t_skip += 1
                continue
        t_non_skip += 1
        new_dataset_list.append(line)

    print("t_skip", t_skip, t_non_skip)

    save_pickle(new_dataset_list, FILTERED_DATASET_W_CONVERTED_TIMESTAMPS)
    
    #dataset_list = load_pickle(DATASET_W_CONVERTED_TIMESTAMPS)
    #save_pickle(dataset_list, FILTERED_DATASET_W_CONVERTED_TIMESTAMPS)

def map_user_and_artist_id_to_labels():
    if create_time_filtered_dataset:
        dataset_list = load_pickle(FILTERED_DATASET_W_CONVERTED_TIMESTAMPS)
    else:
        dataset_list = load_pickle(DATASET_W_CONVERTED_TIMESTAMPS)
    artist_map = {}
    artist_name_map = {}
    user_map = {}
    artist_id = ''
    user_id = ''
    for i in range(len(dataset_list)):
        user_id = dataset_list[i][0]
        artist_id = dataset_list[i][2]
        artist_name = dataset_list[i][2 if dataset == reddit else 3]

        if user_id not in user_map:
            user_map[user_id] = len(user_map)
        if artist_id not in artist_map:
            artist_map[artist_id] = len(artist_map)
            artist_name_map[len(artist_name_map)] = artist_name
        
        dataset_list[i][0] = user_map[user_id]
        dataset_list[i][2] = artist_map[artist_id]

    file = open(dataset + "_map.txt", "w", encoding="utf-8")
    for k, v in artist_name_map.items():
        file.write(str(k) + " " + str(v) + "\n")
    
    # Save to pickle file
    save_pickle(dataset_list, DATASET_USER_ARTIST_MAPPED)

def split_single_session(session):
    splitted = [session[i:i+MAX_SESSION_LENGTH] for i in range(0, len(session), MAX_SESSION_LENGTH)]
    if len(splitted[-1]) < 2:
        del splitted[-1]

    return splitted

def perform_session_splits(sessions):
    splitted_sessions = []
    for session in sessions:
        splitted_sessions += split_single_session(session)

    return splitted_sessions

def split_long_sessions(user_sessions):
    for k, v in user_sessions.items():
        user_sessions[k] = perform_session_splits(v)

def collapse_session(session):
    new_session = [session[0]]
    for i in range(1, len(session)):
        last_event = new_session[-1]
        current_event = session[i]
        if current_event[1] != last_event[1]:
            new_session.append(current_event)

    return new_session


def collapse_repeating_items(user_sessions):
    for k, sessions in user_sessions.items():
        for i in range(len(sessions)):
            sessions[i] = collapse_session(sessions[i])


''' Splits sessions according to inactivity (time between two consecutive 
    actions) and assign sessions to their user. Sessions should be sorted, 
    both eventwise internally and compared to other sessions, but this should 
    be automatically handled since the dataset is presorted
'''
def sort_and_split_usersessions():
    dataset_list = load_pickle(DATASET_USER_ARTIST_MAPPED)
    user_sessions = {}
    current_session = []
    for event in dataset_list:
        user_id = event[0]
        timestamp = event[1]
        artist = event[2]
        
        new_event = [timestamp, artist]

        # if new user -> new session
        if user_id not in user_sessions:
            user_sessions[user_id] = []
            current_session = []
            user_sessions[user_id].append(current_session)
            current_session.append(new_event)
            continue

        # it is an existing user: is it a new session?
        # we also know that the current session contains at least one event
        # NB: Dataset is presorted from newest to oldest events
        last_event = current_session[-1]
        last_timestamp = last_event[0]
        timedelta = timestamp - last_timestamp

        if timedelta < SESSION_TIMEDELTA:
            # new event belongs to current session
            current_session.append(new_event)
        else:
            # new event belongs to new session
            current_session = [new_event]
            user_sessions[user_id].append(current_session)

    collapse_repeating_items(user_sessions)

    # Remove sessions that only contain one event
    # Bad to remove stuff from the lists we are iterating through, so create 
    # a new datastructure and copy over what we want to keep
    new_user_sessions = {}
    for k in user_sessions.keys():
        if k not in new_user_sessions:
            new_user_sessions[k] = []

        us = user_sessions[k]
        for session in us:
            if len(session) > 1 and len(session) < MAX_SESSION_LENGTH_PRE_SPLIT:
                new_user_sessions[k].append(session)

    # Split too long sessions, before removing user with too few sessions
    #  because splitting can result in more sessions.

    split_long_sessions(new_user_sessions)

    # Remove users with less than 3 session
    # Find users with less than 3 sessions first
    to_be_removed = []
    for k, v in new_user_sessions.items():
        if len(v) < MINIMUM_REQUIRED_SESSIONS:
            to_be_removed.append(k)
    # Remove the users we found
    for user in to_be_removed:
        new_user_sessions.pop(user)

    if create_user_statistic_filtered_dataset:
        to_be_removed =  user_avg_session_length_filter(new_user_sessions, remove_above_avg_session_length)
        for user in to_be_removed:
            new_user_sessions.pop(user)

        to_be_removed =  user_avg_session_count_filter(new_user_sessions, remove_above_avg_session_count)
        for user in to_be_removed:
            new_user_sessions.pop(user)

    # Do a remapping to account for removed data
    print("remapping to account for removed data...")

    # remap users
    nus = {}
    for k, v in new_user_sessions.items():
        nus[len(nus)] = new_user_sessions[k]
    
    # remap artistIDs
    art = {}
    for k, v in nus.items():
        sessions = v
        if create_lastfm_cet and len(v) > 1420: #epirically found more or less fill up batches
            sessions = v[-1420:]
        for session in sessions:
            for i in range(len(session)):
                a = session[i][1]
                if a not in art:
                    art[a] = len(art)+1
                session[i][1] = art[a]
        if create_lastfm_cet:
            nus[k] = sessions

    file = open(dataset + "_remap.txt", "w", encoding="utf-8")
    for k, v in art.items():
        file.write(str(k) + " " + str(v) + "\n")

    save_pickle(nus, DATASET_USER_SESSIONS)

# filters out those users that have a higher than average average session length (or lower than average if the higher parameter is set to false)
def user_avg_session_length_filter(new_user_sessions, higher):
    user_avg_session_lengths = [0]*100000
    for k, v in new_user_sessions.items():  # k = user id, v = sessions (list containing lists (sessions) containing lists (tuples of epoch timestamp, event aka artist/subreddit id))
        user_event_count = 0
        user_session_count = 0
        for session in v:
            user_event_count += len(session)
            user_session_count += 1

        user_avg_session_lengths[k] = user_event_count / user_session_count

    to_be_removed = []

    for i in range(len(user_avg_session_lengths)):
        if higher and user_avg_session_lengths[i] > avg_session_length:
            to_be_removed.append(i)
        elif not higher and user_avg_session_lengths[i] < avg_session_length and user_avg_session_lengths[i] > 0:
            to_be_removed.append(i)

    print(len(to_be_removed))

    return to_be_removed

def user_avg_session_count_filter(new_user_sessions, higher):
    user_session_counts = [0]*100000
    for k, v in new_user_sessions.items():  # k = user id, v = sessions (list containing lists (sessions) containing lists (tuples of epoch timestamp, event aka artist/subreddit id))
        user_session_counts[k] = len(v)

    to_be_removed = []

    for i in range(len(user_session_counts)):
        if higher and user_session_counts[i] > avg_session_count:
            to_be_removed.append(i)
        elif not higher and user_session_counts[i] < avg_session_count and user_session_counts[i] > 0:
            to_be_removed.append(i)

    print(len(to_be_removed))

    return to_be_removed

def get_session_lengths(dataset):
    session_lengths = {}
    for k, v in dataset.items():
        session_lengths[k] = []
        for session in v:
            session_lengths[k].append(len(session)-1)

    return session_lengths

def create_padded_sequence(session):
    if len(session) == MAX_SESSION_LENGTH:
        return session

    dummy_timestamp = 0
    dummy_label = 0
    length_to_pad = MAX_SESSION_LENGTH - len(session)
    padding = [[dummy_timestamp, dummy_label]] * length_to_pad
    session += padding
    return session

def pad_sequences(dataset):
    for k, v in dataset.items():
        for session_index in range(len(v)):
            dataset[k][session_index] = create_padded_sequence(dataset[k][session_index])

# Splits the dataset into a training and a testing set, by extracting the last
# sessions of each user into the test set
def split_to_training_and_testing():
    dataset = load_pickle(DATASET_USER_SESSIONS)
    trainset = {}
    testset = {}

    for k, v in dataset.items():
        n_sessions = len(v)
        split_point = int(0.8*n_sessions)
        
        # runtime check to ensure that we have enough sessions for training and testing
        if split_point < 2:
            raise ValueError('User '+str(k)+' with '+str(n_sessions)+""" sessions, 
                resulted in split_point: '+str(split_point)+' which gives too 
                few training sessions. Please check that data and preprocessing 
                is correct.""")
        
        trainset[k] = v[:split_point]
        testset[k] = v[split_point:]

    # Also need to know session lengths for train- and testset
    train_session_lengths = get_session_lengths(trainset)
    test_session_lengths = get_session_lengths(testset)

    # Finally, pad all sequences before storing everything
    pad_sequences(trainset)
    pad_sequences(testset)

    # Put everything we want to store in a dict, and just store the dict with pickle
    pickle_dict = {}
    pickle_dict['trainset'] = trainset
    pickle_dict['testset'] = testset
    pickle_dict['train_session_lengths'] = train_session_lengths
    pickle_dict['test_session_lengths'] = test_session_lengths
    
    save_pickle(pickle_dict , DATASET_TRAIN_TEST_SPLIT)

def create_bpr_mf_sets():
    p = load_pickle(DATASET_TRAIN_TEST_SPLIT)
    train = p['trainset']
    train_sl = p['train_session_lengths']
    test = p['testset']
    test_sl = p['test_session_lengths']

    for user in train.keys():
        extension = test[user][:-1]
        train[user].extend(extension)
        extension = test_sl[user][:-1]
        train_sl[user].extend(extension)
    
    for user in test.keys():
        test[user] = [test[user][-1]]
        test_sl[user] = [test_sl[user][-1]]

    pickle_dict = {}
    pickle_dict['trainset'] = train
    pickle_dict['testset'] = test
    pickle_dict['train_session_lengths'] = train_sl
    pickle_dict['test_session_lengths'] = test_sl
    
    save_pickle(pickle_dict , DATASET_BPR_MF)


if not file_exists(DATASET_W_CONVERTED_TIMESTAMPS):
    print("Converting timestamps.")
    if dataset == reddit:
        convert_timestamps_reddit()
    elif dataset == lastfm:
        convert_timestamps_lastfm()

if create_time_filtered_dataset and not file_exists(FILTERED_DATASET_W_CONVERTED_TIMESTAMPS):
    print("Filtering timestamps")
    filter_timestamps()

if not file_exists(DATASET_USER_ARTIST_MAPPED):
    print("Mapping user and artist IDs to labels.")
    map_user_and_artist_id_to_labels()

if not file_exists(DATASET_USER_SESSIONS):
    print("Sorting sessions to users.")
    sort_and_split_usersessions()

if not file_exists(DATASET_TRAIN_TEST_SPLIT):
    print("Splitting dataset into training and testing sets.")
    split_to_training_and_testing()

if not file_exists(DATASET_BPR_MF):
    print("Creating dataset for BPR-MF.")
    create_bpr_mf_sets()


print("Runtime:", str(time.time()-runtime))
