/**
 * 郵便番号から住所を自動入力する機能を設定します。
 * @param {object} options - 設定オプション
 * @param {string} options.zipcodeFieldId - 郵便番号入力フィールドのID
 * @param {string} options.buttonId - 住所取得ボタンのID
 * @param {string} options.url - 住所情報を取得するAPIのURL
 * @param {Array<object>} options.addressMappings - 住所データをマッピングする設定の配列
 * @param {string} options.apiMessageId - APIからのメッセージを表示する要素のID
 */
function setupZipcodeFetching(options) {
    $('#' + options.buttonId).on('click', function() {
        var zipcode = $('#' + options.zipcodeFieldId).val();
        if (zipcode.length !== 7) {
            alert("郵便番号は7文字で入力してください。");
            return;
        }

        $.ajax({
            url: options.url,
            data: {
                zipcode: zipcode
            },
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    var data = response.data;
                    options.addressMappings.forEach(function(mapping) {
                        var value = '';
                        mapping.from.forEach(function(fromKey) {
                            if (data[fromKey]) {
                                value += data[fromKey];
                            }
                        });
                        $('#' + mapping.to).val(value);
                    });

                    if (options.apiMessageId) {
                        $('#' + options.apiMessageId).html(
                            '<div class="alert alert-info alert-dismissible fade show" role="alert">' +
                            '住所情報を取得しました。' +
                            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
                            '</div>'
                        );
                    }
                } else {
                    alert(response.error);
                }
            },
            error: function() {
                alert("郵便番号の取得に失敗しました。");
            }
        });
    });
}

/**
 * 法人番号から企業情報を自動入力する機能を設定します。
 * @param {object} options - 設定オプション
 * @param {string} options.corporateNumberFieldId - 法人番号入力フィールドのID
 * @param {string} options.buttonId - 企業情報取得ボタンのID
 * @param {string} options.url - 企業情報を取得するAPIのURL
 * @param {object} options.infoMappings - 企業データをマッピングするフィールドのID
 * @param {string} options.apiMessageId - APIからのメッセージを表示する要素のID
 */
function setupCorporateInfoFetching(options) {
    $('#' + options.buttonId).on('click', function() {
        var corporateNumber = $('#' + options.corporateNumberFieldId).val();
        if (corporateNumber.length !== 13) {
            alert("法人番号は13文字で入力してください。");
            return;
        }

        $.ajax({
            url: options.url,
            data: {
                corporate_number: corporateNumber
            },
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    var data = response.data;
                    for (var key in options.infoMappings) {
                        if (options.infoMappings.hasOwnProperty(key) && data[key]) {
                            $('#' + options.infoMappings[key]).val(data[key]);
                        }
                    }

                    if (options.apiMessageId) {
                        $('#' + options.apiMessageId).html(
                            '<div class="alert alert-info alert-dismissible fade show" role="alert">' +
                            '企業情報を取得しました。' +
                            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
                            '</div>'
                        );
                    }
                } else {
                    alert(response.error);
                }
            },
            error: function() {
                alert("企業情報の取得に失敗しました。");
            }
        });
    });
}
