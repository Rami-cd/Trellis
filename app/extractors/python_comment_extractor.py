from typing import Any

def _handle_comments(node: Any) -> list[str]:
    comments = []
    
    curr = node.prev_named_sibling
    while curr and curr.type in ['comment', 'expression_statement']:
        comments.extend(_handle_comments_helper(curr))
        curr = curr.prev_named_sibling

    # body = node.child_by_field_name('body')
    # if body:
    #     for child in body.children:
    #         if child.type == 'expression_statement':
    #             actual_string = child.named_child(0)
    #             if actual_string and actual_string.type == 'string':
    #                 comments.extend(_handle_comments_helper(actual_string))
            
    #         elif child.type == 'comment':
    #             comments.extend(_handle_comments_helper(child))
                
    return comments

def _handle_comments_helper(node: Any) -> list[str]:
    comments = []
    
    if node.type == 'comment':
        comments.append(node.text.decode('utf8').lstrip('#').strip())

    target_node = node
    if node.type == 'expression_statement':
        target_node = node.named_child(0)

    if target_node and target_node.type == 'string':
        content_node = next((c for c in target_node.children if c.type == 'string_content'), None)
        if content_node:
            comments.append(content_node.text.decode('utf8').strip())
        else:
            comments.append(target_node.text.decode('utf8').strip('\'" '))
            
    return comments