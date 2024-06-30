import argparse

from api.uniapp_doc import UniappDoc


def main(type, output_filename):
    # Parse the root URL and extract links and titles
    if type == '1':
        root_url = 'https://doc.dcloud.net.cn'
        homepage_url = '/uni-app-x/'
        downloader = UniappDoc(root_url, homepage_url, output_filename)
    elif type == '2':
        root_url = 'https://doc.dcloud.net.cn'
        homepage_url = '/uni-app-x/uts/'
        downloader = UniappDoc(root_url, homepage_url, output_filename)
    else:
        raise ValueError('Invalid type')
    downloader.run()


if __name__ == '__main__':
    print('Download and merge PDFs from a website.')
    # type = input('Root URL of the website to download PDFs from: ')
    type = input('Type of the website to download PDFs from (1: uniappx 介绍, 2: uniappx uts): ')
    output_filename = input('Output filename for the merged PDF: ')

    # Call the main function with the root URL
    main(type, output_filename)
