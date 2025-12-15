#!/bin/bash

function update_translations() {
    local DOMAIN=$1

    ../../../../../../bin/i18ndude rebuild-pot --pot ${DOMAIN}.pot --create ${DOMAIN} ..
    ../../../../../../bin/i18ndude merge --pot ${DOMAIN}.pot --merge ${DOMAIN}-manual.pot
    ../../../../../../bin/i18ndude sync --pot ${DOMAIN}.pot ./*/LC_MESSAGES/${DOMAIN}.po
}

update_translations 'interaktiv.mcpapi'
#update_translations 'plone'