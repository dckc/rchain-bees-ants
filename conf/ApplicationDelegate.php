<?php
/**
 * A delegate class for the entire application to handle custom handling of
 * some functions such as permissions and preferences.
 */
class conf_ApplicationDelegate {
    /**
     * Returns permissions array.  This method is called every time an action is
     * performed to make sure that the user has permission to perform the action.
     * @param record A Dataface_Record object (may be null) against which we check
     *               permissions.
     * @see Dataface_PermissionsTool
     * @see Dataface_AuthenticationTool
     */
     function getPermissions(&$record){
         $auth =& Dataface_AuthenticationTool::getInstance();
         $user =& $auth->getLoggedInUser();

         $perms = Dataface_PermissionsTool::READ_ONLY();
         if ( !isset($user) ) return $perms;

         $role = $user->val('permission');

         // TODO: managers

         $app =& Dataface_Application::getInstance();
         $query =& $app->getQuery();
         $action = $query['-action'];

         // OK to edit your own stuff
         if ( $record ) {
             $login = $user->val('login');
             if ( $login == $record->getValue('voter') and
                  ($action == 'view_related_record'  or
                   $action == 'view' or
                   $action == 'delete' or
                   $action == 'edit') ) {
                 $perms['edit'] = 1;
                 $perms['delete'] = 1;
             }

             else if ($query['-table'] == 'github_users' and
                      $login == $record->getValue('login') and
                      ($action == 'related_records_list' or
                       $action == 'new_related_record') ) {
                 $perms['add new related record'] = 1;
             }
         }

         // Certify trusted users
         if ( $query['-relationship'] == 'CertifiedBy') {
             $in_listing = $query['-action'] == 'related_records_list';
             $adding = $query['-action'] == 'new_related_record';

             // OK to add certification
             if ( $query['-table'] == 'github_users' ) {

                 if ( $in_listing or $adding ) {
                     $perms['add new related record'] = 1;
                 }
                 else if ($viewing and
                          $app->getRecord()->val('voter') == $user->val('login') ) {
                     $perms['edit'] = 1;
                     $perms['delete'] = 1;
                 }
             }

         }

         // Vote on budgets and rewards
         if ( in_array($query['-relationship'],
                       array('BudgetVotes', 'RewardVotes')) ) {
             $in_listing = $query['-action'] == 'related_records_list';
             $adding = $query['-action'] == 'new_related_record';

             // OK to add vote to issue, budget, or reward
             if ( in_array($query['-table'], array('issue', 'issue_budget', 'reward')) ) {
                 // TODO: $perms['copy'] = 1;

                 if ( $in_listing or $adding ) {
                     $perms['add new related record'] = 1;
                 }
                 else if ($viewing and
                          $app->getRecord()->val('voter') == $user->val('login') ) {
                     $perms['edit'] = 1;
                     $perms['delete'] = 1;
                 }
             }

         }

         if ($query['-table'] == 'invoice_info') {
             // TODO: only your own!
             $perms = Dataface_PermissionsTool::getRolePermissions('DELETE');
         }
         return $perms;
     }

    public function beforeHandleRequest(){
        $app =& Dataface_Application::getInstance();
        $app->addHeadContent(
                sprintf('<link rel="stylesheet" type="text/css" href="%s"/>',
                        htmlspecialchars(DATAFACE_SITE_URL.'/rchain-style.css')
                )
            );

        $query =& $app->getQuery();
        if ( $query['-table'] == 'admin_settings' and
             $query['-action'] != 'edit' ){
            $query['-action'] = 'dashboard';
        }
        
        ###################
		#Here I check to see if they are coming from the Discord login. If they are, we need to check to see if they are a coop member.
		if(array_key_exists('discord_oauth_callback', $query) && $query['discord_oauth_callback'] == 'true')
		{
			$auth =& Dataface_AuthenticationTool::getInstance();
			$user =& $auth->getLoggedInUser();
			#make sure they are actually logged in
			if(isset($user))
			{
				$discordOauth = new discordOauthClass();
				#validate the user
				$discordUser = $discordOauth->checkIfUserValidCoopMember();  # or die trying
                    global $ini_array;
					#then save the validation flag to database
					$user->setValue($ini_array['verified_coop_column'], intval($discordUser->getId()));
                    $user->save(); 
			}
		}
    }

    function block__before_left_column() {
        echo "<ul>\n";
        echo "<li><a href='https://www.rchain.coop/'>RChain Co-op</a></li>\n";
        echo "<li><a href='https://github.com/rchain/Members/blob/master/CONTRIBUTING.md'>RAM Guide</a></li>\n";
        echo "</ul>\n";
    }
}

class VoteAuth {
     function voter__default() {
         $auth =& Dataface_AuthenticationTool::getInstance();
         $user =& $auth->getLoggedInUser();
         return $user->val('login');
     }

    function voter__permissions(&$record) {
        return view_only();
    }
}

class PayPeriodVote extends VoteAuth {
    function pay_period__default () {
        $res = df_query("select current_pay_period from admin_settings", null, true);
        if ( !$res ) throw new Exception(mysql_error(df_db()));
        $pp = $res[0]['current_pay_period'];
        return $pp;
    }

    function pay_period__permissions(&$record) {
        return view_only();
    }
}


function view_only() {
    $perms = Dataface_PermissionsTool::NO_ACCESS();
    $perms['view']=1;
    return $perms;
}
?>
