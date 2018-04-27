angular.module('portal', [
  'ngAria',
  'ngMaterial',
  'ngMessages',
  'ngMdIcons',
  'ngResource',
  'ngSanitize',
  'ui.router',
  'vAccordion',
  'mdPickers',
  'bw.paging',
  'ui.select',
  'io.dennis.contextmenu',
  'lfNgMdFileInput'
])
  .factory('api', function($http, $q) {
    function getCookie(name) {
      var cookieValue = null;
      if (document.cookie && document.cookie !== '') {
          var cookies = document.cookie.split(';');
          for (var i = 0; i < cookies.length; i++) {
              var cookie = jQuery.trim(cookies[i]);
              // Does this cookie string begin with the name we want?
              if (cookie.substring(0, name.length + 1) === (name + '=')) {
                  cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                  break;
              }
          }
      }
      return cookieValue;
    }
    function get(model, filter){
      var defer = $q.defer();
      if (filter) {
        $http.get('/api/v1/import/' + model + '/?' + jQuery.param(filter)).
          success(function (data, status){
            defer.resolve({data: data, status: status});
          }).
          error(function (msg, status) {
            defer.resolve({msg: msg, status: status});
          });
      } else {
        $http.get('/api/v1/import/' + model + '/').
          success(function (data, status){
            defer.resolve({data: data, status: status});
          }).
          error(function (msg, status) {
            defer.resolve({msg: msg, status: status});
          });
      }
      return defer.promise
    }
    function post(model, data){
      var defer = $q.defer();
      $http.post('/api/v1/import/' + model + '/', data, {headers: {'X-CSRFToken': getCookie('csrftoken')}}).
        success(function (data, status){
          defer.resolve({data: data, status: status});
        }).
        error(function (msg, status) {
          defer.resolve({msg: msg, status: status});
        });
      return defer.promise
    }
    function put(model, id, data) {
      var defer = $q.defer();
      $http.put('/api/v1/import/' + model + '/' + id + '/', data, {headers: {'X-CSRFToken': getCookie('csrftoken')}}).
        success(function (data, status){
          defer.resolve({data: data, status: status});
        }).
        error(function (msg, status) {
          defer.resolve({msg: msg, status: status});
        });
      return defer.promise
    }
    function patch(model, id, data) {
      var defer = $q.defer();
      $http.patch('/api/v1/import/' + model + '/' + id + '/', data, {headers: {'X-CSRFToken': getCookie('csrftoken')}}).
        success(function (data, status){
          defer.resolve({data: data, status: status});
        }).
        error(function (msg, status) {
          defer.resolve({msg: msg, status: status});
        });
      return defer.promise
    }

    function del(model, id) {
      var defer = $q.defer();
      $http.delete('/api/v1/import/' + model + '/' + id + '/', {headers: {'X-CSRFToken': getCookie('csrftoken')}}).
        success(function (data, status){
          defer.resolve({data: data, status: status});
        }).
        error(function (msg, status) {
          defer.resolve({msg: msg, status: status});
        });
      return defer.promise
    }
    return {
      get: get,
      post: post,
      put: put,
      patch: patch,
      delete: del,
      getCookie: getCookie
    }
  })
  .factory('api_app', function($http, $q) {
    function getCookie(name) {
      var cookieValue = null;
      if (document.cookie && document.cookie !== '') {
          var cookies = document.cookie.split(';');
          for (var i = 0; i < cookies.length; i++) {
              var cookie = jQuery.trim(cookies[i]);
              // Does this cookie string begin with the name we want?
              if (cookie.substring(0, name.length + 1) === (name + '=')) {
                  cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                  break;
              }
          }
      }
      return cookieValue;
    }
    function get(model, filter){
      var defer = $q.defer();
      if (filter) {
        $http.get('/api/v1/' + model + '/?' + jQuery.param(filter)).
          success(function (data, status){
            defer.resolve({data: data, status: status});
          }).
          error(function (msg, status) {
            defer.resolve({msg: msg, status: status});
          });
      } else {
        $http.get('/api/v1/' + model + '/').
          success(function (data, status){
            defer.resolve({data: data, status: status});
          }).
          error(function (msg, status) {
            defer.resolve({msg: msg, status: status});
          });
      }
      return defer.promise
    }
    function post(model, data){
      var defer = $q.defer();
      $http.post('/api/v1/' + model + '/', data, {headers: {'X-CSRFToken': getCookie('csrftoken')}}).
        success(function (data, status){
          defer.resolve({data: data, status: status});
        }).
        error(function (msg, status) {
          defer.resolve({msg: msg, status: status});
        });
      return defer.promise
    }
    function put(model, id, data) {
      var defer = $q.defer();
      $http.put('/api/v1/' + model + '/' + id + '/', data, {headers: {'X-CSRFToken': getCookie('csrftoken')}}).
        success(function (data, status){
          defer.resolve({data: data, status: status});
        }).
        error(function (msg, status) {
          defer.resolve({msg: msg, status: status});
        });
      return defer.promise
    }
    function patch(model, id, data) {
      var defer = $q.defer();
      $http.patch('/api/v1/' + model + '/' + id + '/', data, {headers: {'X-CSRFToken': getCookie('csrftoken')}}).
        success(function (data, status){
          defer.resolve({data: data, status: status});
        }).
        error(function (msg, status) {
          defer.resolve({msg: msg, status: status});
        });
      return defer.promise
    }

    function del(model, id) {
      var defer = $q.defer();
      $http.delete('/api/v1/' + model + '/' + id + '/', {headers: {'X-CSRFToken': getCookie('csrftoken')}}).
        success(function (data, status){
          defer.resolve({data: data, status: status});
        }).
        error(function (msg, status) {
          defer.resolve({msg: msg, status: status});
        });
      return defer.promise
    }
    return {
      get: get,
      post: post,
      put: put,
      patch: patch,
      delete: del,
      getCookie: getCookie
    }
  })
  .controller('SchemaList', function($scope, api, $mdDialog, $filter, $http){
    api.get('data_schema').then(function(resp){
      $scope.schema_list = resp.data.results;
    });
    $scope.loadData = function () {
      var formData = new FormData();
      formData.append('schema', $scope.import.schema);
      formData.append('error_handling', $scope.import.error_handling);
      angular.forEach($scope.import.files, function(obj){
        if(!obj.isRemote){
          formData.append('files', obj.lfFile);
        }
      });
      $http({
        url: '/api/v1/import/data/',
        method: 'POST',
        data: formData,
        headers: { 'Content-Type': undefined, 'X-CSRFToken': api.getCookie('csrftoken')},
        transformRequest: angular.identity
      }).success(function (){
        $mdDialog.show(
          $mdDialog.alert()
            .parent(angular.element(document.querySelector('.inputdemoBasicUsage')))
            .clickOutsideToClose(true)
            .title('Import complete!')
            .textContent('You can close this window.')
            .ariaLabel('Alert Dialog Demo')
            .ok('Got it!')
        );
      }).error(function (msg) {
        $mdDialog.show(
          $mdDialog.alert()
            .parent(angular.element(document.querySelector('.inputdemoBasicUsage'))).clickOutsideToClose(true)
            .title(msg).textContent('You can close this window.').ariaLabel('Alert Dialog Demo').ok('Ok!')
        );
      })
    };
    $scope.update = function () {
      $scope.selectedItem = $filter('filter')($scope.schema_list, {id: parseInt($scope.import.schema)}, true)[0];
    };
    $scope.openModal = function(ev, model) {
      if (model){
        api.get('schema_fields', {schema_id: $scope.selectedItem.id}).then(function (resp) {
          $scope.field_list = resp.data;
          $mdDialog.show({
            controller: DialogController,
            templateUrl: '/static/js/update_schema.html',
            parent: angular.element(document.body),
            targetEvent: ev,
            clickOutsideToClose:true,
            fullscreen: $scope.customFullscreen,
            locals : {
                data: null,
                vm: null,
                schema: $scope.selectedItem,
                field_list: $scope.field_list,
                item: null
            }
          })
          .then(function(answer) {
            $scope.status = 'You said the information was "' + answer + '".';
          }, function() {
            $scope.status = 'You cancelled the dialog.';
          });
        });
      } else {
        $mdDialog.show({
          controller: DialogController,
          templateUrl: '/static/js/update_schema.html',
          parent: angular.element(document.body),
          targetEvent: ev,
          clickOutsideToClose:true,
          fullscreen: $scope.customFullscreen,
          locals : {
            data: null,
            vm: null,
            schema: null,
            field_list: null,
            item: null
          }
        })
        .then(function(answer) {
          $scope.status = 'You said the information was "' + answer + '".';
        }, function() {
          $scope.status = 'You cancelled the dialog.';
        });
      }
    };
    function DialogController($scope, $mdDialog, api, schema, field_list, item, data, vm, api_app) {
      $scope.data = data;
      $scope.vm = vm;
      $scope.schema = schema;
      $scope.mapping = {'value': null, 'name': null};
      $scope.field_list = field_list;
      $scope.selectedModel = function (model, model_id) {
        return (model.id === model_id)
      };
      api.get('content_type').then(function (resp){
        $scope.models = resp.data.results;
      });

      if (schema) {
        $scope.$watch('schema.model', function(newVal, oldVal){
          api.get('schema_matching', {schema_id: $scope.schema.id}).then(function (resp) {
            $scope.matching_list = resp.data;
          })
        });
      }
      $scope.copyField = function(){
        if ($scope.field_list == null) {
          $scope.field_list = {};
        }
        var last_num = 0;
        if ($scope.field_list.length > 0) {
          last_num = $scope.field_list[$scope.field_list.length - 1].num + 1;
        }
        $scope.field_list.push({num: last_num, source: 'source', target: 'target', schema: schema.id});
      };
      $scope.removeField = function(item, index){
        $scope.field_list.splice(index, 1);
        api.delete('schema_fields', item.id).then(function(resp){})
      };
      $scope.$watch('mapping.model', function (newVal, oldVal) {
        if (newVal !== oldVal) {
          var id = newVal.split(',')[0];
          api.get('content_type/' + id + '/fields').then(function (resp){
            $scope.data.fields = resp.data.results;
          })
        }
      });
      $scope.saveSchema = function(){
        api.post('schema_fields', {'field_list': $scope.field_list, 'matching_list': $scope.matching_list, 'schema_name': $scope.schema.name, 'schema_model': $scope.model}).then(function(resp){
          $scope.hide()
        });
      };
      $scope.hide = function() {
        $mdDialog.hide();
      };
      $scope.cancel = function() {
        $mdDialog.cancel();
      };
      $scope.answer = function(answer) {
        $mdDialog.hide(answer);
      };
      $scope.openExpressionDialog = function(ev, item){
        var vm = $scope;
        vm.readyStatus = {
            expression: false
        };

        vm.item = item;
        var getFunctionsHelp = function() {
          return [
            {
              "name": "To string",
              "description": "<p>Any value to string</p>",
              "func": "str(a)"
            },
            {
              "name": "Contains",
              "description": "<p>String a contains or not in string b</p>",
              "func": "contains(a, b)"
            },
            {
              "name": "To integer",
              "description": "<p>Convert string to integer</p>",
              "func": "int(a)"
            },
            {
              "name": "To float",
              "description": "<p>Convert string to number</p>",
              "func": "float(a)"
            },
            {
              "name": "Round",
              "description": "<p>Match round float</p>",
              "func": "round(number)"
            },
            {
              "name": "Trunc",
              "description": "<p>Match truncate float</p>",
              "func": "trunc(a)"
            },
            {
              "name": "Is close",
              "description": "<p>Compare to float numbers to equality</p>",
              "func": "isclose(a, b)"
            },
            {
              "name": "iff",
              "description": "<p>Return a if x is True else v2</p>",
              "func": "iff(expr, a, b)"
            },
            {
              "name": "Now",
              "description": "<p>Current date</p>",
              "func": "now()"
            },
            {
              "name": "Date",
              "description": "<p>Create date object</p>",
              "func": "date(year, month=1, day=1)"
            },
            {
              "name": "Days",
              "description": "<p>Create timedelta object for operations with dates <br/> now() - days(10)<br/> now() + days(10)</p>",
              "func": "days(a)"
            },
            {
              "name": "Weeks",
              "description": "<p>Create timedelta object for operations with dates <br/> now() - weeks(10)<br/> now() + weeks(10)</p>",
              "func": "weeks(a)"
            },
            {
              "name": "Months",
              "description": "<p>Create timedelta object for operations with dates <br/> now() - months(10)<br/> now() + months(10)</p>",
              "func": "months(a)"
            },
            {
              "name": "Timedelta",
              "description": "<p>General timedelta creation</p><p>years, months, weeks, days:<br/> Relative information, may be negative (argument is plural); adding or subtracting a relativedelta with relative information performs the corresponding aritmetic operation on the original datetime value with the information in the relativedelta.</p><p>leapdays:<br/> Will add given days to the date found, if year is a leap year, and the date found is post 28 of february.</p>",
              "func": "timedelta(years=0, months=0, days=0, leapdays=0, weeks=0)"
            },
            {
              "name": "Add days",
              "description": "<p>Same as date + days(x)</p>",
              "func": "add_days(date, days)"
            },
            {
              "name": "Add weeks",
              "description": "<p>Same as d + days(x * 7)</p>",
              "func": "add_weeks(date, days)"
            },
            {
              "name": "Add workdays",
              "description": "<p>Add 'x' work days to d</p>",
              "func": "add_workdays(date, workdays)"
            },
            {
              "name": "Format date",
              "description": "<p>format date (default format is '%Y-%m-%d')</p>",
              "func": "format_date(date, format='%Y-%m-%d')"
            },
            {
              "name": "Parse date",
              "description": "<p>parse date from string (default format is '%Y-%m-%d')</p>",
              "func": "parse_date(date_string, format='%Y-%m-%d')"
            },
            {
              "name": "Format number",
              "description": "<p>format float number<br/> <br/> decimal_sep:<br/> Decimal separator symbol (for example '.')<br/> decimal_pos:<br/> Number of decimal positions<br/> grouping:<br/> Number of digits in every group limited by thousand separator<br/> thousand_sep:<br/> Thousand separator symbol (for example ',')<br/> use_grouping:<br/> use thousand separator</p>",
              "func": "format_number(number, decimal_sep='.', decimal_pos=None, grouping=3, thousand_sep='', use_grouping=False)"
            },
            {
              "name": "Parse number",
              "description": "<p>same as float(a)</p>",
              "func": "parse_number(a)"
            },
            {
              "name": "Simple price",
              "description": "<p>calculate price on date using 2 point (date1, value1) and (date2, value2)</p>",
              "func": "simple_price(date, date1, value1, date2, value2)"
            }
          ]
        };
        vm.expressions = getFunctionsHelp();
        vm.readyStatus.expression = true;
        vm.selectedHelpItem = vm.expressions[0];
        vm.selectHelpItem = function(item) {
            vm.expressions.forEach(function(expr) {
                expr.isSelected = false;
            });

            item.isSelected = true;

            vm.selectedHelpItem = item;
        };

        vm.appendFunction = function(item) {
            var val = $('#editorExpressionInput')[0].value;
            var cursorPosition = val.slice(0, ($('#editorExpressionInput')[0].selectionStart + '')).length;

            if (cursorPosition == 0) {
                vm.item.expression = vm.item.expression + item.func;
            } else {
                vm.item.expression = vm.item.expression.slice(0, cursorPosition) + item.func + vm.item.expression.slice(cursorPosition);

            }
        };

        vm.cancel = function() {
            $mdDialog.cancel();
        };

        vm.agree = function() {
            api.patch('schema_matching', item.id, {'expression': item.expression});
            $mdDialog.hide({
                status: 'agree',
                data: {
                    item: vm.item
                }
            });
        };

        vm.openHelp = function($event) {
            $mdDialog.show({
                controller: 'HelpDialogController as vm',
                templateUrl: 'views/dialogs/help-dialog-view.html',
                targetEvent: $event,
                locals: {
                    data: {}
                },
                preserveScope: true,
                autoWrap: true,
                skipHide: true
            })
        };
        $mdDialog.show({
            controller: DialogController,
            templateUrl: '/static/js/expression-editor-dialog-view.html',
            parent: angular.element(document.body),
            targetEvent: ev,
            clickOutsideToClose:true,
            fullscreen: $scope.customFullscreen,
            locals : {
              data: {models: $scope.models},
              vm: vm,
              item: item,
              schema: null,
              field_list: null
            }
          })
          .then(function(answer) {
            $scope.status = 'You said the information was "' + answer + '".';
          }, function() {
            $scope.status = 'You cancelled the dialog.';
          });
      };
      $scope.openMapping = function (ev, item) {
        var vm = $scope;
        vm.readyStatus = {
            content: false
        };
        vm.entityItems = [];
        // vm.mapItem = mapItem;
        // vm.mapEntityType = mapItem.complexExpressionEntity;
        vm.mapItem = {};
        vm.mapEntityType = '';
        vm.toggleQuery = function() {
            vm.queryStatus = !vm.queryStatus;
            vm.query = {};
        };
        vm.bindEntityName = function(item) {
            if (item.hasOwnProperty('scheme_name')) {
                return item.scheme_name;
            }
            return item.name;
        };
        vm.setSort = function(propertyName) {
            vm.direction = (vm.sort === propertyName) ? !vm.direction : false;
            vm.sort = propertyName;
        };
        vm.addMapping = function(item, index) {
            item.mapping.splice(index, 0, {
                value: ''
            });
        };

        vm.removeMapping = function(item, mappingItem, index) {
          if (mappingItem.hasOwnProperty('id')) {
            mappingItem.isDeleted = true;
          } else {
            item.mapping.splice(index, 1);
          }

        };
        vm.fancyEntity = function() {
            return vm.mapEntityType.replace('_', ' ');
        };
        function addChilds(classifier, item) {
          vm.entityItems.push({
              value_type: classifier.value_type,
              classifier: classifier.id,
              name: item.name,
              id: item.id,
              level: item.level
          });

          if (item.children && item.children.length > 0) {
              item.children.forEach(function(childItem) {
                  addChilds(classifier, childItem);
              })
          }
        }

        // if (vm.mapEntityType == 'classifier') {
        //     instrumentAttributeTypeService.getByKey(vm.mapItem.attribute_type).then(function(data) {
        //
        //         console.log('classifier data', data);
        //
        //         [data].forEach(function(classifier) {
        //
        //             console.log('classifier', classifier);
        //
        //             classifier.classifiers.forEach(function(item) {
        //
        //                 addChilds(classifier, item);
        //
        //             })
        //         });
        //
        //         api.getList(vm.mapEntityType).then(function(data) {
        //             if (data.hasOwnProperty('results')) {
        //                 vm.items = data.results;
        //             } else {
        //                 vm.items = data
        //             }
        //
        //             console.log('vm.items', vm.items);
        //
        //             var i, e;
        //             for (e = 0; e < vm.entityItems.length; e = e + 1) {
        //                 for (i = 0; i < vm.items.length; i = i + 1) {
        //                     if (vm.items[i].classifier == vm.entityItems[e].id) {
        //
        //                         if (!vm.entityItems[e].hasOwnProperty('mapping')) {
        //                             vm.entityItems[e].mapping = [];
        //                         }
        //
        //                         vm.entityItems[e].mapping.push(vm.items[i])
        //
        //                         //vm.entityItems[e].mapping = vm.items[i]
        //                     }
        //                 }
        //             }
        //
        //             vm.entityItems.forEach(function(entityItem) {
        //                 if (!entityItem.hasOwnProperty('mapping')) {
        //                     entityItem.mapping = [{
        //                         value: ''
        //                     }];
        //                 }
        //             });
        //             vm.readyStatus.content = true;
        //             $scope.$apply();
        //         });
        //     })
        // } else {
        //     // vm.entityMapDashed = vm.mapEntityType.split('_').join('-');
        // }
        var app;
        if (item.model_field = 'account') {
          app = 'accounts/'
        } else {
          app = 'counterparties/'
        }
        api_app.get(app + item.model_field).then(function (resp) {
          vm.entityItems = resp.data.results;
          api.get(item.model_field + '-mapping').then(function(resp) {
            vm.items = resp.data.results;
            var i, e;
            for (e = 0; e < vm.entityItems.length; e = e + 1) {
              for (i = 0; i < vm.items.length; i = i + 1) {
                if (vm.items[i].content_object == vm.entityItems[e].id) {
                  if (!vm.entityItems[e].hasOwnProperty('mapping')) {
                      vm.entityItems[e].mapping = [];
                  }
                  vm.entityItems[e].mapping.push(vm.items[i])
                }
              }
            }
            vm.entityItems.forEach(function(entityItem) {
                if (!entityItem.hasOwnProperty('mapping')) {
                    entityItem.mapping = [{
                        value: ''
                    }];
                }
            });
            vm.readyStatus.content = true;
            $mdDialog.show({
              controller: MappingController,
              templateUrl: '/static/js/entity-type-mapping-dialog-view.html',
              // parent: angular.element(document.body),
              targetEvent: ev,
              clickOutsideToClose:true,
              fullscreen: $scope.customFullscreen,
              autoWrap: false,
              locals : {
                data: {models: $scope.models},
                item: item,
                schema: null,
                vm: vm,
                field_list: null
              }
            });
          });
        });
        vm.cancel = function() {
            $mdDialog.cancel();
        };
        vm.agree = function() {

            var i = 0;

            function updateRow() {
                if (i < vm.entityItems.length) {
                    if (!vm.entityItems[i].hasOwnProperty('mapping')) {
                        i = i + 1;
                        updateRow();
                        return false;
                    }

                    if (vm.entityItems[i].mapping.length) {

                        vm.entityItems[i].mapping.forEach(function(mapItem) {

                            if (!mapItem.hasOwnProperty('id')) {
                                mapItem.provider = 1; //TODO FIND PROVIDER ID?
                                if (vm.mapEntityType == 'classifier') {

                                    mapItem['attribute_type'] = vm.entityItems[i].classifier;

                                    if (vm.entityItems[i].value_type == 30) {
                                        mapItem.classifier = vm.entityItems[i].id
                                    }
                                    mapItem.content_object = mapItem.attribute_type;

                                } else {
                                    //vm.entityItems[i].mapping[vm.mapEntityType] = vm.entityItems[i].id;
                                    mapItem.content_object = vm.entityItems[i].id;
                                }

                                console.log('mapItem', mapItem);
                                console.log('vm.entityItems[i]', vm.entityItems[i]);

                                return api.post(vm.mapEntityType, mapItem).then(function() {
                                    i = i + 1;
                                    updateRow();
                                    return false;
                                })
                            }
                            if (mapItem.isDeleted == true) {
                                return api.delete(vm.mapEntityType, mapItem.id).then(function() {
                                    i = i + 1;
                                    updateRow();
                                    return false;
                                })
                            }
                            return api.patch(vm.mapEntityType, mapItem.id, mapItem).then(function() {
                                i = i + 1;
                                updateRow();
                                return false;
                            })
                        })
                    }
                }
            }

            updateRow();

            $mdDialog.hide({
                status: 'agree'
            });
        };
      };
    }
    function MappingController($scope, $mdDialog, data, item, schema, vm, field_list) {
      $scope.vm = vm;
      $scope.saveMapping = function (mapping) {
        var model = mapping.model.split(',')[1];
        api.patch('schema_matching', item.id, {model_field: model + ':' + mapping.field});
        $mdDialog.hide();
      };
      $scope.vm.cancel = function() {
        $mdDialog.hide();
      };
      $scope.vm.agree = function() {
        var i = 0;
        function updateRow() {
            if (i < vm.entityItems.length) {
                if (!vm.entityItems[i].hasOwnProperty('mapping')) {
                    i = i + 1;
                    updateRow();
                    return false;
                }

                if (vm.entityItems[i].mapping.length) {

                    vm.entityItems[i].mapping.forEach(function(mapItem) {

                        if (!mapItem.hasOwnProperty('id')) {
                            mapItem.provider = 1; //TODO FIND PROVIDER ID?
                            if (vm.mapEntityType == 'classifier') {

                                mapItem['attribute_type'] = vm.entityItems[i].classifier;

                                if (vm.entityItems[i].value_type == 30) {
                                    mapItem.classifier = vm.entityItems[i].id
                                }
                                mapItem.content_object = mapItem.attribute_type;

                            } else {
                                //vm.entityItems[i].mapping[vm.mapEntityType] = vm.entityItems[i].id;
                                mapItem.content_object = vm.entityItems[i].id;
                            }

                            console.log('mapItem', mapItem);
                            console.log('vm.entityItems[i]', vm.entityItems[i]);

                            return api.post(vm.mapEntityType, mapItem).then(function() {
                                i = i + 1;
                                updateRow();
                                return false;
                            })
                        }
                        if (mapItem.isDeleted == true) {
                            return api.delete(vm.mapEntityType, mapItem.id).then(function() {
                                i = i + 1;
                                updateRow();
                                return false;
                            })
                        }
                        return api.patch(vm.mapEntityType, mapItem.id, mapItem).then(function() {
                            i = i + 1;
                            updateRow();
                            return false;
                        })
                    })
                }
            }
        }

        updateRow();

        $mdDialog.hide({
            status: 'agree'
        });
    };
    }
  })
  .config(function($mdThemingProvider) {
    $mdThemingProvider.theme('docs-dark', 'default').primaryPalette('yellow').dark();
  })
  .filter('trustAsHtml', ['$sce', function($sce) {return function (val){
      if (val) {
        return $sce.trustAsHtml(val.toString());
      }
    }
  }]);
