var g_tab_right;
var g_accordion_left;
var g_tree_servers;
var g_tree_example;
var area = null;
var g_tree_menu;
var g_selected_treenode_id;
var g_data_tree_server = [{id:"root",type: "root", text:"服务器列表", isexpand:false, children:[]}];
$(function ()
{
 
    window.addEventListener('message',function(e){
        //console.log("e.source=" + e.source);
        console.log("host=" + e.data.host + ", port=" + e.data.port);
        AddServer(e.data);
    },false);
 
    //布局
    $("#layout1").ligerLayout({ leftWidth: 190, height: '100%',heightDiff:-34,space:4, onHeightChanged: f_heightChanged });

    var height = $(".l-layout-center").height();

    //Tab
    $("#framecenter").ligerTab({ height: height });

    //面板
    $("#accordion1").ligerAccordion({ height: height - 24, speed: null });

    $(".l-link").hover(function ()
    {
        $(this).addClass("l-link-over");
    }, function ()
    {
        $(this).removeClass("l-link-over");
    });
    
    g_tree_menu = $.ligerMenu({ top: 100, left: 100, width: 120, items:
    [
        { id:'cxtmenu_treenode_server_add', text: '连接', click: function(item){
            f_addTab("add_server", "新增连接", 'pymongoadmin_add_server.html'); 
        }, icon: 'add'},
        { id:'cxtmenu_treenode_server_refresh', text: '刷新', click: function(item){
        
        }, icon: 'refresh'},
        //{ line: true },
        { id:'cxtmenu_treenode_server_disconnect', text: '断开', click: function(item){
        
        }, icon: 'delete'}
    ]
    });
    
    //$("#toptoolbar").ligerToolBar({ items: [
        //{
            //text: '增加', 
            //click: function (item){
                //alert(item.text);
            //}, 
            //icon:'add'
        //},
        //{ line:true },
        //{ 
            //text: '刷新', 
            //click: function (item){
                //alert(item.text);
            //}, 
            //icon:'refresh' 
        //},
        //{ line:true },
        //{ 
            //text: '删除', 
            //click: function (item){
                //alert(item.text);
            //}, 
            //icon:'delete' 
        //}
        //]
    //});
    $("#tree_servers").ligerTree({
        //url:'/get?op=get_mongo_hirachy',
        data : g_data_tree_server,
        checkbox: false,
        slide: false,
        nodeWidth: 120,
        //attribute: ['id','line_code','line_name','voltage','category','length','manage_length','start_point','end_point','start_tower','end_tower','status','maintenace','management','owner','team','responsible','investor','designer','supervisor','constructor','operator','finish_date','production_date','decease_date'],
        onContextmenu: function (node, e)
        { 
            g_selected_treenode_id = node.data.id;
            var type = node.data.type;
            console.log("contextmenu=" + g_selected_treenode_id);
            g_tree_menu.show({ top: e.pageY, left: e.pageX });
            if(type == 'root')
            {
                g_tree_menu.setDisabled("cxtmenu_treenode_server_add");
            }
            if(type == 'server')
            {
                g_tree_menu.setDisabled("cxtmenu_treenode_server_add");
            }
            return false;
        },
        onSelect: function(node)
        {
            g_selected_treenode_id = node.data.id;
            console.log("select=" + g_selected_treenode_id);
        }
    });

    g_tree_servers = $("#tree_servers").ligerGetTreeManager();
    
    
    
    
    
    $("#tree1").ligerTree({
        data : indexdata,
        checkbox: false,
        slide: false,
        nodeWidth: 120,
        attribute: ['nodename', 'url'],
        onSelect: function (node)
        {
            if (!node.data.url) return;
            var tabid = $(node.target).attr("tabid");
            if (!tabid)
            {
                tabid = new Date().getTime();
                $(node.target).attr("tabid", tabid)
            } 
            f_addTab(tabid, node.data.text, node.data.url);
        }
    });
    
    

    g_tab_right = $("#framecenter").ligerGetTabManager();
    g_accordion_left = $("#accordion1").ligerGetAccordionManager();
    g_tree_example = $("#tree1").ligerGetTreeManager();
    $("#pageloading").hide();

});

function DisableAllTreeMenu()
{
    g_tree_menu.setDisabled("cxtmenu_treenode_server_add");
}
function AddServer(param)
{
    $.ajax({
        async:true,
        type: "GET",
        url: "/get?op=get_mongodb_server_tree",
        dataType: "json",
        data:param,
        success: function(data)
        { 
            if(data.result)
            {
                if(data.result.data)
                {
                    g_tree_servers.setData(data.result.data);
                }
            }
            //var treedata = [];
            //for(var i in data)
            //{
                //var tnode = {id:data[i]['id'], pid:data[i]['line_id'],text:data[i]['tower_name']};
                //treedata.push(tnode);
            //}
            //treeobj.append(node.target, treedata);
        },
        error: function (e)
        {
            console.log(e);
        }
    });

}

function f_heightChanged(options)
{
    if (g_tab_right)
        g_tab_right.addHeight(options.diff);
    if (g_accordion_left && options.middleHeight - 24 > 0)
        g_accordion_left.setHeight(options.middleHeight - 24);
}
function f_addTab(tabid, text, url)
{ 
    g_tab_right.addTabItem({ tabid : tabid,text: text, url: url });
}

function getJsonFromUrl() {
  var query = location.search.substr(1);
  var data = query.split("&");
  var result = {};
  for(var i=0; i<data.length; i++) {
    var item = data[i].split("=");
    result[item[0]] = item[1];
  }
  return result;
}