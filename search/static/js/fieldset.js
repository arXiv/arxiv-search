/**
  *     Provides add/remove functionality for fieldsets.
  *
  *     TODO: Tests with multiple fieldsets on the same page? There would
  *     likely be collisions, as written.
  **/

$(function() {
  $("[data-toggle=fieldset]").each(function() {
      var $this = $(this);

      //Add new entry
      $this.find("button[data-toggle=fieldset-add-row]").click(function() {
          var target = $($(this).data("target"));
          var last_item = target.find("[data-toggle=fieldset-entry]:last");
          var new_item = last_item.clone(true, true);

          // Make any elements hidden in the first row visible.
          new_item.find(".fieldset-hidden-on-first-row").each(function() {
            $(this).css("visibility", "visible");
          });

          // Generate a new id number for the new item.
          var elem_id = new_item.find(":input")[0].id;
          var elem_num = parseInt(elem_id.replace(/.*-(\d{1,4})-.*/m, '$1')) + 1;
          new_item.attr('data-id', elem_num);

          // Configure input element(s) in the new item.
          new_item.find(":input").each(function() {
              // Increment the field id.
              var id = $(this).attr('id')
                .replace('-' + (elem_num - 1) + '-', '-' + (elem_num) + '-');

              // Clear any values from the last item.
              $(this).attr('name', id)
                .attr('id', id).val('')
                .removeAttr("checked");

              // Set the value for the input field with the default, if
              // specified.
              var default_value = $(this).attr("default");
              if (default_value) {
                $(this).val(default_value);
              }
          });

          // Clear help text.
          new_item.find(".help").each(function() {
              $(this).empty();
          });

          new_item.show();
          last_item.after(new_item); // Insert the new item below the last.
      });

      //Remove row
      $this.find("button[data-toggle=fieldset-remove-row]").click(function() {
        // var to_remove = $(this).
        if($this.find("[data-toggle=fieldset-entry]").length > 1) {
          var this_row = $(this).closest("div[data-toggle=fieldset-entry]");
          this_row.remove();
        }
      });
  });
});
