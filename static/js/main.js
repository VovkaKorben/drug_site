let myStorage = undefined;
const KEY_ARTICLE = 'HEADERS';
const KEY_THEME = 'theme';
// const DEFAULT_OPENED = [0];
// first paragraph is always opened
const COMMAND_LIST = 0
const COMMAND_SEARCH = 1
const COMMAND_ARTICLE = 2
const STORAGE_UPDATE = 0
const STORAGE_REPLACE = 1
const STORAGE_DELETE = 2

function save_storage(key, value) {
    if (myStorage === undefined)
        myStorage = window.localStorage;
    myStorage.setItem(key, value);
}
function load_storage(key, def) {
    if (myStorage === undefined)
        myStorage = window.localStorage;
    p = myStorage.getItem(key);
    if (p === null)
        p = def;
    return p;
}
function parse_answer(result) {
    if ('storage'in result) {
        $.each(result.storage, function(i, storage_action) {
            switch (storage_action.action) {
            case STORAGE_UPDATE:
                let s = load_storage(storage_action.key, JSON.stringify(storage_action.value));
                s = JSON.parse(s);
                s = Object.assign({}, s, storage_action.value);
                save_storage(storage_action.key, JSON.stringify(s));
                break;
            }
            // console.log(`storage_action: ${storage_action}`);

        });

    }

    if ('dom'in result) {

        jQuery.each(result.dom, function(index, item) {
            elem = $(item.selector);
            if (elem) {
                if ('html'in item)
                    $(elem).html(item.html);
                if ('css_add'in item)
                    jQuery.each(item.css_add, function(index, item) {
                        $(elem).addClass(item);
                    });
                if ('css_remove'in item)
                    jQuery.each(item.css_remove, function(index, item) {
                        $(elem).removeClass(item);
                    });
                if ('attr_set'in item)
                    jQuery.each(item.attr_set, function(k, v) {
                        $(elem).attr(v.attr, v.value);
                        // console.log('[store] ',v.attr,': ',$(elem).attr(v.attr));
                        // console.log('[check] ',$(elem).attr(v.attr));
                    });
            }

        });
    }

}
function send_data(data) {

    fetch('/parse_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    }).then(response => response.json()).then(result => {
        // console.log('Server response:', result);
        parse_answer(result);
        update_commands(result.params);
    }
    ).catch(error => {
        console.error('Error:', error);
    }
    );
}
function update_commands(params) {
    console.log('update_commands:', params);
    if (params.command == COMMAND_LIST || params.command == COMMAND_SEARCH) {

        $('a[data-article]').off("click");
        $('a[data-article]').on("click", function() {
            data = {
                'command': COMMAND_ARTICLE,
                'value': $(this).data('article')
            };
            if (params.command == COMMAND_SEARCH) {
                data['params'] = $('#content').data('lemmas');
            }
            send_data(data);
        });

        $('a[data-category]').off("click");
        $('a[data-category]').on("click", function() {
            data = {
                'command': COMMAND_LIST,
                'value': $(this).data('category')
            };

            send_data(data);
        });

    } else if (params.command == COMMAND_ARTICLE) {

        $('[data-header]').on('click', function() {
            let doc_id = $('#content').attr('data-docid');
            let header_id = $(this).data('header');
            let headers = JSON.parse(load_storage(KEY_ARTICLE, '{}'));

            // get article ID
            let opened_search = headers[doc_id].indexOf(header_id);

            if (opened_search > -1) {
                // hide
                headers[doc_id].splice(opened_search, 1);
                $(this).find('.header_wrapper svg').removeClass('rot90');
                $(this).find('.text_wrapper').slideUp();
            } else {
                // open
                headers[doc_id].push(header_id);

                $(this).find('.header_wrapper svg').addClass('rot90');
                $(this).find('.text_wrapper').slideDown();

            }
            save_storage(KEY_ARTICLE, JSON.stringify(headers));

        })
        // get article ID
        let doc_id = $('#content').attr('data-docid');
        // console.log('doc_id: ',doc_id);
        let headers = JSON.parse(load_storage(KEY_ARTICLE, '{}'));
        if (!(headers.hasOwnProperty(doc_id))) {
            // если у нас нет такой статьи в хранилище, находим первый параграф и пишем его
            let paragraphs = $("#content div[data-header]");
            if (paragraphs.length > 0) {
                let paragraph_id = $(paragraphs[0]).data('header');
                headers[doc_id] = [paragraph_id]
                save_storage(KEY_ARTICLE, JSON.stringify(headers));
            }
        }

        // пробегаем по всем номерам параграфов и закрываем их
        $('[data-header]').each(function() {
            let header_id = $(this).data('header');
            if (!headers[doc_id].includes(header_id)) {

                $(this).find('.header_wrapper svg').removeClass('rot90');
                $(this).find('.text_wrapper').hide();
            }
        });
        if ('scroll'in params) {
            let elem = $(`[data-header=${params.scroll}]`);
            // console.log(elem);
            $('html, body').animate({
                scrollTop: $(elem).offset().top - 70
            }, 1000);
            // alert(params.scroll);
        }
    }
}
function set_theme(theme) {
    theme = parseInt(theme);
    $("link#theme").attr("href", theme ? "css/light.css" : "css/dark.css");
    $('#theme2').attr('xlink:href', theme ? 'svg/icons.svg#dark' : 'svg/icons.svg#light');

}

function do_search() {
    send_data({
        'command': COMMAND_SEARCH,
        'value': $('#search_input').val()
    });
}
$(document).ready(function() {
    // categories list
    $('[data-link="cat_list"]').on('click', function() {
        send_data({
            'command': COMMAND_LIST,
            'value': -1
        });
    });

    // search handler
    $('#search_input').on('keydown', function(ev) {
        if (ev.keyCode == 13)
            do_search();
    });
    $('#search_img').on('click', function() {
        do_search();
    });

    // theme 
    $('svg#theme').on('click', function(params) {
        let theme = load_storage(KEY_THEME, 0);
        theme = 1 - theme;
        save_storage(KEY_THEME, theme);
        set_theme(theme);
    });
    let theme = load_storage(KEY_THEME, 0);
    set_theme(theme);

    // debug code
    //send_data({ 'command': COMMAND_SEARCH, 'value': 'xz' });
    // send_data({        'command': COMMAND_ARTICLE,        'value': 47 ,'params':[185, 598]    });
    // send_data({ 'command': COMMAND_LIST, 'value': 0 });
    // send_data({ 'command': COMMAND_ARTICLE, 'value': 10 });
    send_data({
        'command': COMMAND_LIST,
        'value': -1
    });
    // show all categories with count

    // do_search();
});
