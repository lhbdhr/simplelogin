$('.mailbox-select').multipleSelect()

function confirmDeleteAlias() {
  let that = $(this)
  let alias = that.data('alias-email')
  let aliasDomainTrashUrl = that.data('custom-domain-trash-url')

  let message = `也许您想禁用别名？请注意，一旦删除，<b>无法</b>恢复。`
  if (aliasDomainTrashUrl !== undefined) {
    message = `也许您想禁用别名？删除后，它会移至<a href="${aliasDomainTrashUrl}">垃圾箱</a>`
  }

  bootbox.dialog({
    title: `删除 ${alias}`,
    message: message,
    size: 'large',
    onEscape: true,
    backdrop: true,
    buttons: {
      disable: {
        label: '仅禁用，不删除',
        className: 'btn-primary',
        callback: function () {
          that
            .closest('form')
            .find('input[name="form-name"]')
            .val('disable-alias')
          that.closest('form').submit()
        },
      },

      delete: {
        label: '删除，我已经不再需要它',
        className: 'btn-outline-danger',
        callback: function () {
          that.closest('form').submit()
        },
      },

      cancel: {
        label: '取消删除',
        className: 'btn-outline-primary',
      },
    },
  })
}

$('.enable-disable-alias').change(async function () {
  let aliasId = $(this).data('alias')
  let alias = $(this).data('alias-email')

  await disableAlias(aliasId, alias)
})

async function disableAlias(aliasId, alias) {
  let oldValue
  try {
    let res = await fetch(`/api/aliases/${aliasId}/toggle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (res.ok) {
      let json = await res.json()

      if (json.enabled) {
        toastr.success(`${alias} 已启用`)
        $(`#send-email-${aliasId}`).removeClass('disabled')
      } else {
        toastr.success(`${alias} 已禁用`)
        $(`#send-email-${aliasId}`).addClass('disabled')
      }
    } else {
      toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
      // reset to the original value
      oldValue = !$(this).prop('checked')
      $(this).prop('checked', oldValue)
    }
  } catch (e) {
    toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
    // reset to the original value
    oldValue = !$(this).prop('checked')
    $(this).prop('checked', oldValue)
  }
}

$('.enable-disable-pgp').change(async function (e) {
  let aliasId = $(this).data('alias')
  let alias = $(this).data('alias-email')
  const oldValue = !$(this).prop('checked')
  let newValue = !oldValue

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        disable_pgp: oldValue,
      }),
    })

    if (res.ok) {
      if (newValue) {
        toastr.success(`PGP 已经为 ${alias} 启用`)
      } else {
        toastr.info(`PGP 已经为 ${alias} 禁用`)
      }
    } else {
      toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
      // reset to the original value
      $(this).prop('checked', oldValue)
    }
  } catch (e) {
    toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
    // reset to the original value
    $(this).prop('checked', oldValue)
  }
})

$('.pin-alias').change(async function () {
  let aliasId = $(this).data('alias')
  let alias = $(this).data('alias-email')
  const oldValue = !$(this).prop('checked')
  let newValue = !oldValue

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        pinned: newValue,
      }),
    })

    if (res.ok) {
      if (newValue) {
        toastr.success(`${alias} 已添加为收藏`)
      } else {
        toastr.info(`${alias} 已删除收藏`)
      }
    } else {
      toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
      // reset to the original value
      $(this).prop('checked', oldValue)
    }
  } catch (e) {
    toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
    // reset to the original value
    $(this).prop('checked', oldValue)
  }
})

$('.save-note').on('click', async function () {
  let oldValue
  let aliasId = $(this).data('alias')
  let note = $(`#note-${aliasId}`).val()

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        note: note,
      }),
    })

    if (res.ok) {
      toastr.success(`保存成功`)
    } else {
      toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
      // reset to the original value
      oldValue = !$(this).prop('checked')
      $(this).prop('checked', oldValue)
    }
  } catch (e) {
    toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
    // reset to the original value
    oldValue = !$(this).prop('checked')
    $(this).prop('checked', oldValue)
  }
})

$('.save-mailbox').on('click', async function () {
  let oldValue
  let aliasId = $(this).data('alias')
  let mailbox_ids = $(`#mailbox-${aliasId}`).val()

  if (mailbox_ids.length === 0) {
    toastr.error('你至少需要选择一个收件箱', '错误')
    return
  }

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        mailbox_ids: mailbox_ids,
      }),
    })

    if (res.ok) {
      toastr.success(`收件箱保存成功`)
    } else {
      toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
      // reset to the original value
      oldValue = !$(this).prop('checked')
      $(this).prop('checked', oldValue)
    }
  } catch (e) {
    toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
    // reset to the original value
    oldValue = !$(this).prop('checked')
    $(this).prop('checked', oldValue)
  }
})

$('.save-alias-name').on('click', async function () {
  let aliasId = $(this).data('alias')
  let name = $(`#alias-name-${aliasId}`).val()

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: name,
      }),
    })

    if (res.ok) {
      toastr.success(`发件人名称保存成功`)
    } else {
      toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
    }
  } catch (e) {
    toastr.error('抱歉造成不便！您能否刷新页面并重试？', '未知错误')
  }
})

new Vue({
  el: '#filter-app',
  delimiters: ['[[', ']]'], // necessary to avoid conflict with jinja
  data: {
    showFilter: false,
  },
  methods: {
    async toggleFilter() {
      let that = this
      that.showFilter = !that.showFilter
      store.set('showFilter', that.showFilter)
    },
  },
  async mounted() {
    if (store.get('showFilter')) this.showFilter = true
  },
})
