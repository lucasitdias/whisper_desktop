from app.core.telemetry import ProcessResourceSampler


def test_sampler_calcula_cpu_normalizada_e_ram_sem_dependencia_externa():
    wall_values = iter([10.0, 12.0])
    cpu_values = iter([3.0, 5.0])
    sampler = ProcessResourceSampler(
        clock=lambda: next(wall_values),
        process_clock=lambda: next(cpu_values),
        rss_reader=lambda: 256 * 1024 * 1024,
        processor_count=4,
    )

    snapshot = sampler.sample()

    assert snapshot.cpu_percent == 25.0
    assert snapshot.ram_mb == 256.0
