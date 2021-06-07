import tensorflow as tf
from tensorflow.keras.layers import Layer, LayerNormalization

class SpatialGatingUnit(Layer):
    def __init__(self, 
                dim_seq, 
                causal = False, 
                activation = None, 
                init_eps = 1e-3,
                **kwargs):
        

        self.dim_seq = dim_seq
        self.causal = causal
        self.activation = activation
        self.init_eps = init_eps / dim_seq

        return super(SpatialGatingUnit, self).__init__(**kwargs)

    def build(self, _):
        self.conv1d_bias = tf.Variable(
            tf.ones(shape=[self.dim_seq]), 
            name="sgu_conv1d_bias"
        )

        self.conv1d_kernel = tf.Variable(
            tf.random.uniform(
                shape=(self.dim_seq, self.dim_seq, 1),
                minval=-self.init_eps, 
                maxval=self.init_eps
            ), 
            name="sgu_conv1d_kernel"
        )

        self.norm = LayerNormalization()

    def call(self, x):
        n = x.shape[1]
        weight, bias = self.conv1d_kernel, self.conv1d_bias
        if(self.causal):
            weight, bias = weight[:n, :n], bias[:n]

            mask = tf.ones(weight.shape[:2])

            # band_part and set_diag replace triu(1) in lucidrains' implementation
            mask = tf.linalg.band_part(mask, 0, -1)
            mask = tf.linalg.set_diag(mask, tf.linalg.diag_part(mask) * 0.)
            
            mask = tf.cast(mask, dtype=tf.bool)
            weight = tf.where(mask[..., None], 0., weight)


        res, gate = tf.split(x, 2, axis=-1)
        gate = self.norm(gate)
        conv1d_kwargs = {
            "stride": 1, 
            "use_cudnn_on_gpu": True, 
            "data_format": "NWC"
        }
        gate = tf.nn.conv1d(gate, filters=self.conv1d_kernel, **conv1d_kwargs) + self.conv1d_bias
        if(self.activation is not None):
            gate = self.activation(gate)
        return gate * res
        
