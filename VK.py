import time
import requests
import json
import csv
import networkx as nx
import pandas as pd
import os

access_token = ''
vk_version = 5.154
my_id = 146697287
FILE_PATH = 'Friends.csv'

# Вывод с меткой времени
def out(message,level = 1):
    print('\t'*(level-1)+time.strftime('[%X] ', time.localtime())+message)


def divide_chunks(data, chunk_size):
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

# Получение user_id по сокращенному алиасу пользователя
def get_user_id_by_name(name):
    try:
        response = requests.get('https://api.vk.com/method/users.get',params={
            'user_ids':name,
            'access_token':access_token,
            'v':vk_version
        })
        return int(json.loads(response.text)['response'][0]['id'])
    except:
        print(f"Error\t{response.text}")

# Получение списка списков общих жрузей между source_id и каждым из targed_ids
def get_chunk(source_id,target_ids):
    code = 'return {'
    for target_id in target_ids:
        code += f'"{target_id}":API.friends.getMutual({{"source_id":{source_id},"target_uid":{target_id}}}),'
    code = code[:-1]+'};'
    try:
        response = requests.get('https://api.vk.com/method/execute', params={
            'code': code,
            'access_token': access_token,
            'v': vk_version
        })
        return json.loads(response.text)['response']
    except:
        print(response.text)
        return []

# Получение списка общих друзей
def get_mutual_friends(source,target):
    try:
        response = requests.get('https://api.vk.com/method/friends.getMutual',params={
            'source_uid':source,
            'target_uid':target,
            'access_token': access_token,
            'v': vk_version
        })
        time.sleep(0.3)
        return list(json.loads(response.text)['response'])
    except:
        #print(f"Error\t{response.text}")
        return []

# Получение списка друхей по user_id
def get_friends(user_id):
    try:
        response = requests.get('https://api.vk.com/method/friends.get', params={
            'user_id': int(user_id),
            'count':20000,
            'access_token': access_token,
            'v': vk_version
        })
        time.sleep(0.3)
        return json.loads(response.text)['response']['items']
    except:
        if json.loads(response.text)['error']['error_code'] == 18:
            #print(f'ERROR\t{user_id}\tUser was deleted or banned')
            pass
        elif json.loads(response.text)['error']['error_code'] == 30:
            #print(f'ERROR\t{user_id}\tUser profile is private')
            pass
        else:
            print(response.text)
        time.sleep(0.3)
        return []
        #Обработать возможность ошибки


# Сбор данных при помощи vkscript
def use_vkscript():
    first_friends = get_friends(my_id)
    second_layer = []
    for chunk in divide_chunks(first_friends, 20):
        results = get_chunk(my_id, chunk)
        for i in results:
            if results[i] != False:
                second_layer += results[i]

    second_layer_counter = len(set(second_layer))
    out(f'Start working with second layer [{second_layer_counter}]')
    third_layer = []
    for second_layer_friend in set(second_layer):
        out(f'Work with {second_layer_friend} [{second_layer_counter}]', 2)
        second_friends = get_friends(second_layer_friend)
        for chunk in divide_chunks(second_friends, 20):
            results = get_chunk(second_layer_friend, chunk)
            for i in results:
                if results[i] != False:
                    third_layer += results[i]
                    out(f'Third layer increased [{len(third_layer)}]', 3)
            time.sleep(0.3)
    out(f'Third layer size = [{len(set(third_layer))}]')

def main():
    G = nx.Graph()

    counter = 0
    out('Загрузка графа')
    with open(FILE_PATH, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            G.add_edge(int(row['host']), int(row['friend']))
            counter += 1

    out('Вычисление центральности по собственному вектору') #47 sec
    eigenvector_cent = sorted(list(nx.katz_centrality_numpy(G).items()),
                              key=lambda i: i[1], reverse=True)
    for i in eigenvector_cent[:10]:
        print(i[0], '\t', i[1])

    out('Вычисление центральности по посредничеству ')
    betweenness_cent = sorted(list(nx.betweenness_centrality(G).items()),
                              key=lambda i: i[1], reverse=True)
    for i in betweenness_cent[:10]:
        print(i[0], '\t', i[1])

    out('Вычисление центральности по близости')
    closeness_cent = sorted(list(nx.closeness_centrality(G).items()),
                            key=lambda i: i[1], reverse=True)
    for i in closeness_cent[:10]:
        print(i[0], '\t', i[1])

# Получение всех людей из первого слоя
def get_first_layer():
    if not os.path.isfile(FILE_PATH):
        file = open(FILE_PATH, 'w', encoding='UTF8', newline='')
        writer = csv.writer(file, delimiter=';')
        writer.writerow(['host', 'friend'])
        file.close()
    data = pd.read_csv('VK.csv')
    data = data.drop(columns=['Отметка времени'])
    return [i[0] for i in data.values.tolist()]

# Сохранение связей в файл
def save_friends(owner,friends):
    file = open(FILE_PATH, 'a', encoding='UTF8', newline='')
    writer = csv.writer(file, delimiter=';')
    edges = [[owner, i] for i in friends]
    writer.writerows(edges)
    file.close()

# Выгрузка всех данных о друзьях
def get_all_friends(first_layer):
    counts = []
    file = open(FILE_PATH, 'a', encoding='UTF8',newline='')
    for main_friend in first_layer:
        user_id = get_user_id_by_name(main_friend)
        second_layer = get_friends(user_id)
        counter = len(second_layer)
        edges_counter = counter
        out(f'Work with user {user_id} ({counter})')
        if second_layer != []:
            save_friends(user_id,second_layer)
            for second_friend in second_layer:
                counter -= 1
                out(f'Work with second layer friend {second_friend} [{counter}]',2)
                third_layer = get_friends(second_friend)
                edges_counter += len(third_layer)
                if third_layer != []:
                    save_friends(second_friend, third_layer)
                    for third_friend in third_layer:
                        out(f'Work with third layer friend {third_friend}', 3)
                        four_layer = get_mutual_friends(second_friend,third_layer)
                        if four_layer != []:
                            save_friends(third_friend,four_layer)
                            edges_counter += len(four_layer)
        out(f'User {main_friend} обработан. Кол-во записей {edges_counter}')
        counts.append(edges_counter)
    print(counts)
    print(sum(counts))

main()