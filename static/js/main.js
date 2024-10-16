let myStorage = undefined;
const KEY_ARTICLE = 'HEADERS';
const KEY_THEME = 'theme';
// const DEFAULT_OPENED = [0];
// first paragraph is always opened
const COMMAND_LIST = 0
const COMMAND_SEARCH = 1
const COMMAND_ARTICLE = 2

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
    if ('storage' in result) {
        for (k in result.data) {
            // console.log('data parse_answer:', k, '', result.data[k]);
            save_storage(k, result.data[k]);
        }

    }

    if ('dom' in result) {

        jQuery.each(result.dom, function (index, item) {
            // do something with `item` (or `this` is also `item` if you like)
            elem = $(item.selector);
            if (elem) {
                if ('html' in item)
                    $(elem).html(item.html);
                if ('css_add' in item)
                    jQuery.each(item.css_add, function (index, item) {
                        $(elem).addClass(item);
                    });
                if ('css_remove' in item)
                    jQuery.each(item.css_remove, function (index, item) {
                        $(elem).removeClass(item);
                    });
                if ('attr_set' in item)
                    jQuery.each(item.attr_set, function (k, v) {
                        // $(elem).removeClass(item);
                        $(elem).attr(v[0], v[1]);
                    });
            }

        });
    }
    if ('attr' in result) {

        $.each(result.attr.set, function (key, value) {
            alert(key + ": " + value);
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
    if (params.command == COMMAND_LIST || params.command == COMMAND_SEARCH) {

        $('a[data-article]').off("click");
        $('a[data-article]').on("click", function () {
            data = {
                'command': COMMAND_ARTICLE,
                'value': $(this).data('article'),
                'params': $('#content').data('lemmas')
            };
            send_data(data);
        });

        /* 
         $('[data-article]').on('click', function () {
 
             send_data({
                 'command': COMMAND_ARTICLE,
                 'value': $(this).data('article')
             });
 
         });*/
    } else if (params.command == COMMAND_ARTICLE) {

        $('[data-header]').on('click', function () {
            const header_id = $(this).data('header');
            let headers = JSON.parse(load_storage(KEY_ARTICLE, '{}'));
            const main_id = $('#content').data('articleid'); // get article ID
            const opened_search = headers[main_id].indexOf(header_id);

            if (opened_search > -1) {
                // hide
                headers[main_id].splice(opened_search, 1);
                $(this).children('img').removeClass('rot90');
                $(this).siblings('div').slideUp();
            } else {
                // open
                headers[main_id].push(header_id);

                $(this).children('img').addClass('rot90');
                $(this).siblings('div').slideDown();
            }
            save_storage(KEY_ARTICLE, JSON.stringify(headers));

        })

        let main_id = $('#content').data('articleid'); // get article ID
        let headers = JSON.parse(load_storage(KEY_ARTICLE, '{}'));
        if (!(headers.hasOwnProperty(main_id))) { // if article not exists, let the first paragraph open
            // если у нас нет такой статьи в хранилище, находим первый параграф и пишем его
            let first_paragraph = $("#content > div:first-child > div:first-child");
            if (first_paragraph.length > 0) {
                first_paragraph_id = $(first_paragraph[0]).data('header');
                headers[main_id] = [first_paragraph_id]
                save_storage(KEY_ARTICLE, JSON.stringify(headers));
            }
        }

        // пробегаем по всем номерам параграфов и закрываем их
        $('[data-header]').each(function () {
            let header_id = $(this).data('header');
            if (!headers[main_id].includes(header_id)) {

                $(this).children('img').removeClass('rot90');
                $(this).siblings('div').hide();
            }
        });
    }
}
function set_theme(theme) {
    theme = parseInt(theme);
    $("link#theme").attr("href", theme ? "css/light.css" : "css/dark.css");
    $("img#theme").attr("src", theme ? "img/dark.png" : "img/light.png");
    $("img#logo").attr("src", theme ? "img/logolight.png" : "img/logodark.png");
    // $("link#theme").attr("href",theme ? "css/light.css":"css/dark.css");  
    //    <img id="theme" src="img/light.png" width="32" height="32" alt="" />
}
function update_links() {
    $('a[data-article]').off("click");
    $('a[data-article]').on("click", function () {
        send_data({
            'command': COMMAND_ARTICLE,
            'value': $(this).data('article')
        });
    });
    // .off( "click", "#theone", flash )

}

$(document).ready(function () {
    // categories list
    $('img#cat_menu').on('click', function () {
        $('div#cat_list').show();
    });

    $('[data-list]').on('click', function () {
        $('div#cat_list').hide();
        send_data({
            'command': COMMAND_LIST,
            'value': $(this).data('list')
        });
    });

    // update_commands();
    $('.search_input').on('input', function () {
        send_data({
            'command': COMMAND_SEARCH,
            'value': $(this).val()
        });
    });

    // debug code
    send_data({ 'command': COMMAND_SEARCH, 'value': 'цирроз печени' });
    // send_data({ 'command': COMMAND_ARTICLE, 'value': 14 });

    // theme 
    $('img#theme').on('click', function (params) {
        let theme = load_storage(KEY_THEME, 0);
        theme = 1 - theme;
        save_storage(KEY_THEME, theme);
        set_theme(theme);
    });
    let theme = load_storage(KEY_THEME, 0);
    set_theme(theme);
});
