$('.mailbox-select').multipleSelect();

function confirmDeleteAlias() {
  let that = $(this);
  let alias = that.data("alias-email");
  let aliasDomainTrashUrl = that.data("custom-domain-trash-url");

  let message = `也许您想禁用别名？请注意，一旦删除，<b>无法</b>恢复。`;
  if (aliasDomainTrashUrl !== undefined) {
    message = `也许您想禁用别名？删除后，它会移至域
    <a href="${aliasDomainTrashUrl}">垃圾箱</a>`;
  }

  bootbox.dialog({
    title: `删除 ${alias}`,
    message: message,
    size: 'large',
    onEscape: true,
    backdrop: true,
    buttons: {
      disable: {
        label: '禁用别名',
        className: 'btn-primary',
        callback: function () {
          that.closest("form").find('input[name="form-name"]').val("disable-alias");
          that.closest("form").submit();
        }
      },

      delete: {
        label: "确认删除，我已经不需要它了",
        className: 'btn-outline-danger',
        callback: function () {
          that.closest("form").submit();
        }
      },

      cancel: {
        label: '取消',
        className: 'btn-outline-primary'
      },

    }
  });
}

$(".enable-disable-alias").change(async function () {
  let aliasId = $(this).data("alias");
  let alias = $(this).data("alias-email");

  await disableAlias(aliasId, alias);
});

function getHeaders() {
  return {
    "Content-Type": "application/json",
    "X-Sl-Allowcookies": 'allow',
  }
}

async function disableAlias(aliasId, alias) {
  let oldValue;
  try {
    let res = await fetch(`/api/aliases/${aliasId}/toggle`, {
      method: "POST",
      headers: getHeaders()
    });

    if (res.ok) {
      let json = await res.json();

      if (json.enabled) {
        toastr.success(`${alias} is enabled`);
        $(`#send-email-${aliasId}`).removeClass("disabled");
      } else {
        toastr.success(`${alias} is disabled`);
        $(`#send-email-${aliasId}`).addClass("disabled");
      }
    } else {
      toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
      // reset to the original value
      oldValue = !$(this).prop("checked");
      $(this).prop("checked", oldValue);
    }
  } catch (e) {
    toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
    // reset to the original value
    oldValue = !$(this).prop("checked");
    $(this).prop("checked", oldValue);
  }
}

$(".enable-disable-pgp").change(async function (e) {
  let aliasId = $(this).data("alias");
  let alias = $(this).data("alias-email");
  const oldValue = !$(this).prop("checked");
  let newValue = !oldValue;

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: "PUT",
      headers: getHeaders(),
      body: JSON.stringify({
        disable_pgp: oldValue,
      }),
    });

    if (res.ok) {
      if (newValue) {
        toastr.success(`PGP 已经为 ${alias} 启用`);
      } else {
        toastr.info(`PGP 已经为 ${alias} 禁用`);
      }
    } else {
      toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
      // reset to the original value
      $(this).prop("checked", oldValue);
    }
  } catch (err) {
    toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
    // reset to the original value
    $(this).prop("checked", oldValue);
  }
});

$(".pin-alias").change(async function () {
  let aliasId = $(this).data("alias");
  let alias = $(this).data("alias-email");
  const oldValue = !$(this).prop("checked");
  let newValue = !oldValue;

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: "PUT",
      headers: getHeaders(),
      body: JSON.stringify({
        pinned: newValue,
      }),
    });

    if (res.ok) {
      if (newValue) {
        toastr.success(`${alias} 已置顶`);
      } else {
        toastr.info(`${alias} 已取消置顶`);
      }
    } else {
      toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
      // reset to the original value
      $(this).prop("checked", oldValue);
    }
  } catch (e) {
    toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
    // reset to the original value
    $(this).prop("checked", oldValue);
  }
});

async function handleNoteChange(aliasId, aliasEmail) {
  const note = document.getElementById(`note-${aliasId}`).value;

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: "PUT",
      headers: getHeaders(),
      body: JSON.stringify({
        note: note,
      }),
    });

    if (res.ok) {
      toastr.success(`已保存 ${aliasEmail} 的描述`);
    } else {
      toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
    }
  } catch (e) {
    toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
  }

}

function handleNoteFocus(aliasId) {
  document.getElementById(`note-focus-message-${aliasId}`).classList.remove('d-none');
}

function handleNoteBlur(aliasId) {
  document.getElementById(`note-focus-message-${aliasId}`).classList.add('d-none');
}

async function handleMailboxChange(aliasId, aliasEmail) {
  const selectedOptions = document.getElementById(`mailbox-${aliasId}`).selectedOptions;
  const mailbox_ids = Array.from(selectedOptions).map((selectedOption) => selectedOption.value);

  if (mailbox_ids.length === 0) {
    toastr.error("您必须至少选择一个邮箱", "错误");
    return;
  }

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: "PUT",
      headers: getHeaders(),
      body: JSON.stringify({
        mailbox_ids: mailbox_ids,
      }),
    });

    if (res.ok) {
      toastr.success(`已为 ${aliasEmail} 更新邮箱`);
    } else {
      toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
    }
  } catch (e) {
    toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
  }

}

async function handleDisplayNameChange(aliasId, aliasEmail) {
  const name = document.getElementById(`alias-name-${aliasId}`).value;

  try {
    let res = await fetch(`/api/aliases/${aliasId}`, {
      method: "PUT",
      headers: getHeaders(),
      body: JSON.stringify({
        name: name,
      }),
    });

    if (res.ok) {
      toastr.success(`已为 ${aliasEmail} 保存显示名称`);
    } else {
      toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
    }
  } catch (e) {
    toastr.error("抱歉造成不便！您可以刷新页面并重试吗？", "未知错误");
  }

}

function handleDisplayNameFocus(aliasId) {
  document.getElementById(`display-name-focus-message-${aliasId}`).classList.remove('d-none');
}

function handleDisplayNameBlur(aliasId) {
  document.getElementById(`display-name-focus-message-${aliasId}`).classList.add('d-none');
}

new Vue({
  el: '#filter-app',
  delimiters: ["[[", "]]"], // necessary to avoid conflict with jinja
  data: {
    showFilter: false,
    showStats: false
  },
  methods: {
    async toggleFilter() {
      let that = this;
      that.showFilter = !that.showFilter;
      store.set('showFilter', that.showFilter);
    },

    async toggleStats() {
      let that = this;
      that.showStats = !that.showStats;
      store.set('showStats', that.showStats);
    }
  },
  async mounted() {
    if (store.get("showFilter"))
      this.showFilter = true;

    if (store.get("showStats"))
      this.showStats = true;
  }
});
