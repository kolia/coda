# Design

### code representation

Code is represented as S-expressions, which are just nested lists of S-expressions or literals. The reason for this is that S-expressions are simple. For python, this means AST that is simply flattened into S-expression format. For Julia, the AST is already an S-expression.

### evaluator

The evaluator takes an S-expression, transforms it into an AST, and attempts to evaluate the AST. The evaluator returns a Try := Success(Scope) | Failure(Exception), where a Scope is a dictionary mapping names to values.

### graph augmenter

Takes an S-expression, and uses static analysis tools such as jedi to add links between nodes, producing a graph data structure.

### graph embedder

Takes the augmented graph representation of code, runs several passes of message-passing to produce embeddings for each node.

### code generator / decoder

Generates S-expressions, one token at a time, including opening and closing parentheses. List members can either be literals or pointers to symbols that are in scope, including function and class definitions.

Every time a token is emitted, all graph augmentation routines are attempted, and the graph embedder is run for a few passes with new graph edges and vertices if successful, with the position of the current 'cursor' being a special graph vertex. Embeddings are collected in a memory matrix, which is used to drive subsequent generation, where the question asked of the memories is derived from the cursor embedding and problem constraint information.

### structure forcing

In the NLP setting, teacher forcing forces the last emitted token to be what the supervision target dictates before predicting the next token. Teacher forcing uses information that is only available at train time; at test time, the decoder operates blindly by assuming that the token it last emitted was the right one, and it continues. Beam-search relaxes this greediness a little, but the generation is still blind.

Contrary to the NLP setting, the compiler or static analysis tools can provide useful guidance for generating source code **at test time**. We might as well set up our training so that this guidance is put to good use at train and test time: Let's generalize teacher forcing.

We can re-cast teacher forcing as giving the decoder some feedback that it can act upon before predicting the next token. In this new setting, the decoder takes 2 kinds of actions: it modifies its internal state given feedback, and it emits tokens. When the feedback is a teacher forced token, the optimal modification of internal state is the replacement of the last emitted token with the teacher forced one. I propose to make this modification of internal state be learned instead of being hard-coded, openning the way to using other kinds of feedback, of which there are many in the source code generation setting: the compiler or static analysis tool can provide errors, type information, values, and various evaluations of values such as calling to_string.

A simple modification of the decoder to accommodate this could be: 
