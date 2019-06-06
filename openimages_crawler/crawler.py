import collections
import csv
import json
import os
import urllib.request

DESCRIPTIONS_BOXABLE_CSV = 'index/class-descriptions-boxable.csv'
LABELS_HIERARCHY_JSON = 'index/bbox_labels_600_hierarchy.json'

IMAGE_LABELS_TEST_CSV = 'index/test-annotations-human-imagelabels.csv'
IMAGE_LABELS_VALIDATE_CSV = 'index/validation-annotations-human-imagelabels.csv'
IMAGE_LABELS_TRAIN_CSV = 'index/train-annotations-human-imagelabels.csv'
IMAGE_LABELS_CSV = IMAGE_LABELS_TEST_CSV

IMAGE_IDS_TEST_CSV = 'index/test-images-with-rotation.csv'
IMAGE_IDS_TRAIN_CSV = 'index/image_ids_and_rotation.csv'
IMAGE_IDS_CSV = IMAGE_IDS_TEST_CSV

DEFAULT_LICENSE_FILTER = None

def get_class_descriptions(class_ids, index_file=DESCRIPTIONS_BOXABLE_CSV):
    """Get class descriptions from an index file

    :param class_ids: List of classes to search for
    :param index_file: CSV file containing (class_id, description)
    :return: dict with class keys and description values
    """

    # If we get one (not a list), make it a list of one.
    if not isinstance(class_ids, list):
        class_ids = [class_ids]

    class_descriptions = {}

    with open(index_file) as descriptions:
        reader = csv.reader(descriptions)
        for row in reader:
            if row[0] in class_ids:
                class_descriptions[row[0]] = row[1]
                if len(class_descriptions) >= len(class_ids):
                    # Brake if we found them all
                    break

    return class_descriptions


def get_label_names(action, level_filters, grouping_level, license_filter=DEFAULT_LICENSE_FILTER, hierarchy_file=LABELS_HIERARCHY_JSON):

    print('action', action)
    print('grouping_level', grouping_level)
    print('level_filters', level_filters)
    print('license_filter', license_filter)

    level = 1
    ids = {}

    with open(hierarchy_file) as hierarchy:
        json_hierarchy = json.load(hierarchy)

        # top_label = json_hierarchy['LabelName']
        # print('top id', top_label)
        # print('top description', get_class_descriptions([top_label]))

        sub_categories = json_hierarchy['Subcategory']
        level += 1

        # print(get_class_descriptions([x['LabelName'] for x in sub_categories]))

        counter = collections.Counter()  # TODO: don't need counter if I can just use len(class list)
        id_lists = collections.defaultdict(list)  # Map of lists w/ default


        for sub_category in sub_categories:
            # print('filters', level_filters[level])
            # print(get_class_descriptions(sub_category['LabelName']))
            if level_filters and level_filters[level] and get_class_descriptions(sub_category['LabelName'])[sub_category['LabelName']] not in level_filters[level]:
                continue

            # print(sub_category)
            for sub_sub in sub_category.get('Subcategory', ()):

                grouping_label = get_class_descriptions([sub_sub['LabelName']])[sub_sub['LabelName']]
                print("grouping label:", grouping_label)

                for sub_sub_sub in sub_sub.get('Subcategory', ()):
                    print('...' + str(get_class_descriptions([sub_sub_sub['LabelName']])))
                    print(sub_sub_sub)
                    counter[grouping_label] += 1
                    id_lists[grouping_label].append(sub_sub_sub['LabelName'])
                    if 'Subcategory' in sub_sub_sub:
                        labels = [l['LabelName'] for l in sub_sub_sub['Subcategory']]
                        print('..' * 4, get_class_descriptions(labels))
                        counter[grouping_label] += len(labels)  # TODO: maybe use desc counts instead
                        id_lists[grouping_label].extend(labels)

        # TODO: If no subcats, then add labelname to group ids
        # TODO: Need this at each level and count them
        # TODO: Test if all leaf labels hit urls

        # print('Subcategory: ' + get_class_descs(sub_category['LabelName']).get(sub_category))
        print("Counter:", counter)
        print("ID Lists:", id_lists)

        # Don't need counter anymore because
        for i, l in id_lists.items():
            print("Grouping LabelName:", i)
            print("Sub-Label Count:", len(l))

        return id_lists


def get_image_ids(id_lists, limit, f=IMAGE_LABELS_CSV):

    grouped_image_ids = collections.defaultdict(list)

    with open(f) as imagelabels:
        reader = csv.reader(imagelabels)
        for row in reader:
            image_id = row[0]
            label_name = row[2]

            total = 0
            for group, labels in id_lists.items():
                group_images_found = len(grouped_image_ids[group])
                total += group_images_found
                if group_images_found < limit and label_name in labels:
                    grouped_image_ids[group].append(image_id)
                    total += 1
                    break

            if total >= limit * len(id_lists.keys()):
                # print("HIT LIMIT")
                break

    return grouped_image_ids


def download_thumbnails(image_ids, f=IMAGE_IDS_CSV):

    found = 0
    wanted = 0
    for group, ids in image_ids.items():
        os.makedirs(group, exist_ok=True)
        wanted += len(ids)

    with open("attribution.txt", "w+") as attribution:

        with open(f) as image_details:
            reader = csv.reader(image_details)
            for row in reader:
                image_id = row[0]
                orig_url = row[2]
                landing_url = row[3]
                license = row[4]
                profile = row[5]
                author = row[6]
                title = row[7]
                thumbnail = row[10]
                extension = thumbnail.split('?')[0].split('.')[-1]

                for group, ids in image_ids.items():
                    if image_id in ids:
                        attribution.write("{} Image {} by {} at {} licensed {}\n".format(
                            group, title, author, thumbnail, license))
                        found += 1
                        try:
                            urllib.request.urlretrieve(thumbnail, os.path.join(group, '.'.join((image_id, extension))))
                        except Exception as e:
                            print(e)
                            print("Exception on {}".format(thumbnail))
                            pass
                        break

                if found >= wanted:
                    print("Found all {} images.".format(found))
                    break


# TODO: refactor. Not really using action and grouping level?
group_label_names = get_label_names("count", {2: ['Vehicle']}, 3)

limit = 100
image_ids = get_image_ids(group_label_names, limit)
# print("image ids:", image_ids)
for k, v in image_ids.items():
    print("LabelName:", k)
    print("Image Count:", len(v))

download_thumbnails(image_ids)

# d = get_class_descriptions(['/m/0bl9f', '/m/0242l'])
# grouping_level = 3
# action = "count"  # download_image, download_thumbnail

