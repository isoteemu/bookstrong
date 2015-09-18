function gimmick_search(gimmick) {
    search = new RegExp(gimmick, "i");
    $('.wrestler-rank-item').each(function() {
        if($(this).data('gimmicks').search(search) != -1) {
            $(this).removeClass('gimmick-filter-hide')
        } else {
            $(this).addClass('gimmick-filter-hide')
        }
    })
    rank_page();
}

function rank_page(page) {
    i = 1

    if(! page) {
        page = 1
    }

    under = ( page - 1 ) * items_per_page
    over =  page * items_per_page

    rank_page_nr = page;

    $('a.wrestler-rank-item').each(function() {
        
        $(this).removeClass('limit-filter-hide');
        is_visible = ($(this).css('display') == 'none') ? false : true;
        if(is_visible) {
            if(i <= under || i > over) {
                $(this).addClass('limit-filter-hide');
            }
            i = i + 1
        }
    });

    $('#rank-pagination a').each(function() {
        li = $(this).parent();
        
        pager_nr = $(this).data('page')
        li.removeClass('active');
        li.removeClass('disabled');

        if(pager_nr == page) {
            li.addClass('active');
        } else if(items_per_page * pager_nr > i) {
            li.addClass('disabled');
        }
    });
}
        
function rank_previous_page() {
    if(rank_page_nr <= 1)
        return false;
    return rank_page(rank_page_nr - 1);
}

function rank_next_page() {
    return rank_page(rank_page_nr + 1);
}

$('#wrestler-filter').keyup(function() {
    clearTimeout(gimmick_search_scheduler);
    gimmick = $(this).val();
    gimmick_search_scheduler = setTimeout(function() {gimmick_search(gimmick)}, 250);
})

$('a.promotion-filter').click(function(){
    $('a.promotion-filter').each(function() {$(this).removeClass('active')});

    $(this).addClass('active');
    $('#promotion-filter .txt').html($(this).html());
    promotion = $(this).data('promotion')
    $('nav.rank a').each(function() {
        if(promotion === undefined) {
            $(this).removeClass('promotion-filter-hide');
        } else if($(this).data('promotion') == promotion) {
            $(this).removeClass('promotion-filter-hide');
        } else {
            $(this).addClass('promotion-filter-hide');
        }
    })
    rank_page();
})

$(document).ready(function() {
    var user_lang = navigator.language || navigator.userLanguage;
    if(user_lang.split('-')[0] != 'ja') {
        $('html').attr('lang', 'en');
        $('input[name=lang][id=en]').click();
    }
});
