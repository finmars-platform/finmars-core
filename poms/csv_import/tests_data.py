
class TestData():

    correct_file_rows = [
        ['Name', 'Short name', 'Account', 'Country', 'Pay Date', 'Fee', 'Responsible'],
        ['DIR20_name', 'DIR20', 'account_2', 'Russia', '2017-01-01', '2.0', 'res_1'],
        ['DIR21_name', 'DIR21', 'account_2', 'France', '2017-02-01', '4.2', 'res_1'],
        ['DIR22_name', 'DIR22', 'account_2', 'Germany', '2017-03-04', '51.2', 'res_1'],
        ['DIR23_name', 'DIR23', 'account_2', 'USA', '2017-05-06', '32.4', 'res_1']
    ]

    correct_small_file_rows = [
        ['Name', 'Short name', 'Account', 'Country'],
        ['DIR20_name', 'DIR20', 'account_2', 'Russia'],
        ['DIR21_name', 'DIR21', 'account_2', 'France'],
        ['DIR22_name', 'DIR22', 'account_2', 'Germany'],
        ['DIR23_name', 'DIR23', 'account_2', 'USA']
    ]

    error_relation_mapping_rows = [
        ['Name', 'Short name', 'Account', 'Country', 'Pay Date', 'Fee', 'Responsible'],
        ['DIR20_name', 'DIR20', 'account_4', 'Russia', '2017-01-01', '2.0', 'res_1'],
        ['DIR21_name', 'DIR21', 'account_2', 'France', '2017-02-01', '4.2', 'res_2'],
        ['DIR22_name', 'DIR22', 'account_5', 'Germany', '2017-03-04', '51.2', 'res_1'],
        ['DIR23_name', 'DIR23', 'account_2', 'USA', '2017-05-06', '32.4', 'res_1']
    ]
