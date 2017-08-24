use "buffered"
use "wallaroo"
use "wallaroo/source"
use "wallaroo/source/kafka_source"
use "wallaroo/sink/kafka_sink"
use "wallaroo/topology"

actor Main
  new create(env: Env) =>
    try
      if (env.args(1) == "--help") or (env.args(1) == "-h") then
        KafkaSourceConfigCLIParser.print_usage(env.out)
        KafkaSinkConfigCLIParser.print_usage(env.out)
        return
      end
    else
      KafkaSourceConfigCLIParser.print_usage(env.out)
      KafkaSinkConfigCLIParser.print_usage(env.out)
      return
    end

    try
      let application = recover val
        Application("Celsius Conversion App")
          .new_pipeline[F32, F32]("Celsius Conversion",
            KafkaSourceConfig[F32](KafkaSourceConfigCLIParser(env.args, env.out)
              , env.root as AmbientAuth, CelsiusKafkaDecoder))
            .to[F32]({(): Multiply => Multiply})
            .to[F32]({(): Add => Add})
            .to_sink(KafkaSinkConfig[F32](FahrenheitEncoder,
              KafkaSinkConfigCLIParser(env.args, env.out), env.root as AmbientAuth))
      end
      Startup(env, application, "celsius-conversion")
    else
      @printf[I32]("Couldn't build topology\n".cstring())
    end

primitive Multiply is Computation[F32, F32]
  fun apply(input: F32): F32 =>
    input * 1.8

  fun name(): String => "Multiply by 1.8"

primitive Add is Computation[F32, F32]
  fun apply(input: F32): F32 =>
    input + 32

  fun name(): String => "Add 32"

primitive FahrenheitEncoder
  fun apply(f: F32, wb: Writer): (Array[ByteSeq] val, None) =>
    wb.f32_be(f)
    (wb.done(), None)

primitive CelsiusKafkaDecoder is SourceHandler[F32]
  fun decode(a: Array[U8] val): F32 ? =>
    let r = Reader
    r.append(a)
    r.f32_be()